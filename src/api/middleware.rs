//! API middleware

use actix_web::{
    dev::{forward_ready, Service, ServiceRequest, ServiceResponse, Transform},
    http::header::AUTHORIZATION,
    Error, HttpMessage,
};
use futures::future::{ok, LocalBoxFuture, Ready};
use std::rc::Rc;

use crate::security::auth::{AuthService, Claims};

/// JWT authentication middleware
pub struct JwtAuth {
    auth_service: AuthService,
    /// Paths that don't require authentication
    excluded_paths: Vec<String>,
}

impl JwtAuth {
    pub fn new(auth_service: AuthService) -> Self {
        Self {
            auth_service,
            excluded_paths: vec![
                "/health".to_string(),
                "/api/v1/auth/login".to_string(),
            ],
        }
    }

    pub fn exclude_path(mut self, path: &str) -> Self {
        self.excluded_paths.push(path.to_string());
        self
    }
}

impl<S, B> Transform<S, ServiceRequest> for JwtAuth
where
    S: Service<ServiceRequest, Response = ServiceResponse<B>, Error = Error> + 'static,
    B: 'static,
{
    type Response = ServiceResponse<B>;
    type Error = Error;
    type Transform = JwtAuthMiddleware<S>;
    type InitError = ();
    type Future = Ready<Result<Self::Transform, Self::InitError>>;

    fn new_transform(&self, service: S) -> Self::Future {
        ok(JwtAuthMiddleware {
            service: Rc::new(service),
            auth_service: self.auth_service.clone(),
            excluded_paths: self.excluded_paths.clone(),
        })
    }
}

pub struct JwtAuthMiddleware<S> {
    service: Rc<S>,
    auth_service: AuthService,
    excluded_paths: Vec<String>,
}

impl<S, B> Service<ServiceRequest> for JwtAuthMiddleware<S>
where
    S: Service<ServiceRequest, Response = ServiceResponse<B>, Error = Error> + 'static,
    B: 'static,
{
    type Response = ServiceResponse<B>;
    type Error = Error;
    type Future = LocalBoxFuture<'static, Result<Self::Response, Self::Error>>;

    forward_ready!(service);

    fn call(&self, req: ServiceRequest) -> Self::Future {
        let path = req.path().to_string();
        let service = Rc::clone(&self.service);

        // Check if path is excluded
        if self.excluded_paths.iter().any(|p| path.starts_with(p)) {
            return Box::pin(async move { service.call(req).await });
        }

        let auth_service = self.auth_service.clone();

        Box::pin(async move {
            // Extract token from Authorization header
            let token = req
                .headers()
                .get(AUTHORIZATION)
                .and_then(|h| h.to_str().ok())
                .and_then(|h| h.strip_prefix("Bearer "));

            match token {
                Some(token) => {
                    // Validate token
                    match auth_service.validate_token(token) {
                        Ok(claims) => {
                            // Store claims in request extensions
                            req.extensions_mut().insert(claims);
                            service.call(req).await
                        }
                        Err(_) => {
                            Err(actix_web::error::ErrorUnauthorized("Invalid or expired token"))
                        }
                    }
                }
                None => Err(actix_web::error::ErrorUnauthorized("Missing authorization token")),
            }
        })
    }
}

/// Request extension trait for getting claims
pub trait ClaimsExt {
    fn get_claims(&self) -> Option<Claims>;
}

impl ClaimsExt for actix_web::HttpRequest {
    fn get_claims(&self) -> Option<Claims> {
        self.extensions().get::<Claims>().cloned()
    }
}

/// Rate limiting middleware (token bucket)
pub struct RateLimiter {
    requests_per_minute: u32,
}

impl RateLimiter {
    pub fn new(requests_per_minute: u32) -> Self {
        Self { requests_per_minute }
    }
}

impl<S, B> Transform<S, ServiceRequest> for RateLimiter
where
    S: Service<ServiceRequest, Response = ServiceResponse<B>, Error = Error> + 'static,
    B: 'static,
{
    type Response = ServiceResponse<B>;
    type Error = Error;
    type Transform = RateLimiterMiddleware<S>;
    type InitError = ();
    type Future = Ready<Result<Self::Transform, Self::InitError>>;

    fn new_transform(&self, service: S) -> Self::Future {
        ok(RateLimiterMiddleware {
            service: Rc::new(service),
            _requests_per_minute: self.requests_per_minute,
        })
    }
}

pub struct RateLimiterMiddleware<S> {
    service: Rc<S>,
    _requests_per_minute: u32,
}

impl<S, B> Service<ServiceRequest> for RateLimiterMiddleware<S>
where
    S: Service<ServiceRequest, Response = ServiceResponse<B>, Error = Error> + 'static,
    B: 'static,
{
    type Response = ServiceResponse<B>;
    type Error = Error;
    type Future = LocalBoxFuture<'static, Result<Self::Response, Self::Error>>;

    forward_ready!(service);

    fn call(&self, req: ServiceRequest) -> Self::Future {
        let service = Rc::clone(&self.service);

        // In production, implement proper rate limiting with Redis
        // For now, just pass through
        Box::pin(async move { service.call(req).await })
    }
}
