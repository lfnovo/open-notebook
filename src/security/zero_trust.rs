//! Zero Trust middleware for WireGuard IP validation

use actix_web::{
    dev::{forward_ready, Service, ServiceRequest, ServiceResponse, Transform},
    Error, HttpResponse,
};
use futures::future::{ok, LocalBoxFuture, Ready};
use ipnetwork::IpNetwork;
use std::{
    net::IpAddr,
    rc::Rc,
    str::FromStr,
};

/// Zero Trust configuration
#[derive(Debug, Clone)]
pub struct ZeroTrustConfig {
    /// Allowed IP ranges (e.g., WireGuard subnet)
    pub allowed_networks: Vec<IpNetwork>,
    /// Whether to enforce Zero Trust
    pub enabled: bool,
    /// Allow localhost for development
    pub allow_localhost: bool,
}

impl Default for ZeroTrustConfig {
    fn default() -> Self {
        Self {
            allowed_networks: vec![
                IpNetwork::from_str("10.0.0.0/24").unwrap(), // WireGuard default
            ],
            enabled: true,
            allow_localhost: true,
        }
    }
}

impl ZeroTrustConfig {
    /// Check if an IP is allowed
    pub fn is_allowed(&self, ip: &IpAddr) -> bool {
        if !self.enabled {
            return true;
        }

        // Allow localhost in dev mode
        if self.allow_localhost && ip.is_loopback() {
            return true;
        }

        // Check if IP is in any allowed network
        self.allowed_networks.iter().any(|net| net.contains(*ip))
    }
}

/// Zero Trust middleware
pub struct ZeroTrustMiddleware {
    config: Rc<ZeroTrustConfig>,
}

impl ZeroTrustMiddleware {
    pub fn new(config: ZeroTrustConfig) -> Self {
        Self {
            config: Rc::new(config),
        }
    }
}

impl<S, B> Transform<S, ServiceRequest> for ZeroTrustMiddleware
where
    S: Service<ServiceRequest, Response = ServiceResponse<B>, Error = Error> + 'static,
    B: 'static,
{
    type Response = ServiceResponse<B>;
    type Error = Error;
    type Transform = ZeroTrustMiddlewareService<S>;
    type InitError = ();
    type Future = Ready<Result<Self::Transform, Self::InitError>>;

    fn new_transform(&self, service: S) -> Self::Future {
        ok(ZeroTrustMiddlewareService {
            service: Rc::new(service),
            config: Rc::clone(&self.config),
        })
    }
}

pub struct ZeroTrustMiddlewareService<S> {
    service: Rc<S>,
    config: Rc<ZeroTrustConfig>,
}

impl<S, B> Service<ServiceRequest> for ZeroTrustMiddlewareService<S>
where
    S: Service<ServiceRequest, Response = ServiceResponse<B>, Error = Error> + 'static,
    B: 'static,
{
    type Response = ServiceResponse<B>;
    type Error = Error;
    type Future = LocalBoxFuture<'static, Result<Self::Response, Self::Error>>;

    forward_ready!(service);

    fn call(&self, req: ServiceRequest) -> Self::Future {
        let config = Rc::clone(&self.config);
        let service = Rc::clone(&self.service);

        Box::pin(async move {
            // Get client IP
            let client_ip = req
                .connection_info()
                .realip_remote_addr()
                .and_then(|ip| ip.split(':').next())
                .and_then(|ip| IpAddr::from_str(ip).ok());

            match client_ip {
                Some(ip) if config.is_allowed(&ip) => {
                    // IP is allowed, proceed with request
                    service.call(req).await
                }
                Some(ip) => {
                    // IP not allowed
                    tracing::warn!(ip = %ip, "Zero Trust: Blocked unauthorized IP");
                    Err(actix_web::error::ErrorForbidden("Access denied: IP not in allowed range"))
                }
                None => {
                    // Could not determine IP
                    tracing::warn!("Zero Trust: Could not determine client IP");
                    Err(actix_web::error::ErrorForbidden("Access denied: Unable to verify client"))
                }
            }
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::net::IpAddr;

    #[test]
    fn test_zero_trust_config() {
        let config = ZeroTrustConfig::default();

        // Localhost should be allowed
        let localhost: IpAddr = "127.0.0.1".parse().unwrap();
        assert!(config.is_allowed(&localhost));

        // WireGuard range should be allowed
        let wg_ip: IpAddr = "10.0.0.5".parse().unwrap();
        assert!(config.is_allowed(&wg_ip));

        // External IP should be blocked
        let external_ip: IpAddr = "8.8.8.8".parse().unwrap();
        assert!(!config.is_allowed(&external_ip));
    }
}
