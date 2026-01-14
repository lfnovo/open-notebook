//! Authentication service with JWT

use anyhow::{Context, Result};
use argon2::{
    password_hash::{rand_core::OsRng, PasswordHash, PasswordHasher, PasswordVerifier, SaltString},
    Argon2,
};
use chrono::{Duration, Utc};
use jsonwebtoken::{decode, encode, DecodingKey, EncodingKey, Header, Validation};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// JWT claims
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct Claims {
    pub sub: String,        // User ID
    pub email: String,
    pub role: UserRole,
    pub exp: i64,           // Expiration time
    pub iat: i64,           // Issued at
    pub jti: String,        // JWT ID (for revocation)
}

/// User roles
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum UserRole {
    Admin,
    User,
    ReadOnly,
}

/// Authentication service
pub struct AuthService {
    jwt_secret: String,
    jwt_expiry_hours: i64,
    argon2: Argon2<'static>,
}

impl AuthService {
    /// Create new auth service
    pub fn new(jwt_secret: String, jwt_expiry_hours: u64) -> Self {
        Self {
            jwt_secret,
            jwt_expiry_hours: jwt_expiry_hours as i64,
            argon2: Argon2::default(),
        }
    }

    /// Hash a password
    pub fn hash_password(&self, password: &str) -> Result<String> {
        let salt = SaltString::generate(&mut OsRng);
        let hash = self
            .argon2
            .hash_password(password.as_bytes(), &salt)
            .map_err(|e| anyhow::anyhow!("Failed to hash password: {}", e))?;
        Ok(hash.to_string())
    }

    /// Verify a password
    pub fn verify_password(&self, password: &str, hash: &str) -> Result<bool> {
        let parsed_hash =
            PasswordHash::new(hash).map_err(|e| anyhow::anyhow!("Invalid hash format: {}", e))?;

        Ok(self
            .argon2
            .verify_password(password.as_bytes(), &parsed_hash)
            .is_ok())
    }

    /// Generate JWT token
    pub fn generate_token(&self, user_id: &str, email: &str, role: UserRole) -> Result<String> {
        let now = Utc::now();
        let exp = now + Duration::hours(self.jwt_expiry_hours);

        let claims = Claims {
            sub: user_id.to_string(),
            email: email.to_string(),
            role,
            exp: exp.timestamp(),
            iat: now.timestamp(),
            jti: Uuid::new_v4().to_string(),
        };

        let token = encode(
            &Header::default(),
            &claims,
            &EncodingKey::from_secret(self.jwt_secret.as_bytes()),
        )
        .context("Failed to generate JWT token")?;

        Ok(token)
    }

    /// Validate and decode JWT token
    pub fn validate_token(&self, token: &str) -> Result<Claims> {
        let token_data = decode::<Claims>(
            token,
            &DecodingKey::from_secret(self.jwt_secret.as_bytes()),
            &Validation::default(),
        )
        .context("Invalid or expired token")?;

        Ok(token_data.claims)
    }

    /// Refresh token (generate new token with same claims)
    pub fn refresh_token(&self, token: &str) -> Result<String> {
        let claims = self.validate_token(token)?;
        self.generate_token(&claims.sub, &claims.email, claims.role)
    }
}

impl Clone for AuthService {
    fn clone(&self) -> Self {
        Self {
            jwt_secret: self.jwt_secret.clone(),
            jwt_expiry_hours: self.jwt_expiry_hours,
            argon2: Argon2::default(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_password_hashing() {
        let auth = AuthService::new("secret".to_string(), 24);
        let hash = auth.hash_password("mypassword123").unwrap();
        assert!(auth.verify_password("mypassword123", &hash).unwrap());
        assert!(!auth.verify_password("wrongpassword", &hash).unwrap());
    }

    #[test]
    fn test_jwt_generation() {
        let auth = AuthService::new("secret".to_string(), 24);
        let token = auth
            .generate_token("user123", "user@example.com", UserRole::User)
            .unwrap();

        let claims = auth.validate_token(&token).unwrap();
        assert_eq!(claims.sub, "user123");
        assert_eq!(claims.email, "user@example.com");
        assert_eq!(claims.role, UserRole::User);
    }
}
