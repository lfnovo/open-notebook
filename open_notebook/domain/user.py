"""
User domain model for authentication.
"""

from datetime import datetime
from typing import ClassVar, Optional

from loguru import logger
from pydantic import field_validator

from open_notebook.database.repository import repo_query
from open_notebook.domain.base import ObjectModel
from open_notebook.exceptions import DatabaseOperationError, InvalidInputError
from open_notebook.utils.password import hash_password, verify_password


class User(ObjectModel):
    """User model for authentication."""
    
    table_name: ClassVar[str] = "user"
    email: str
    password_hash: str
    last_login: Optional[datetime] = None

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, v: str) -> str:
        """Validate email format."""
        if not v or not v.strip():
            raise InvalidInputError("Email cannot be empty")
        # Basic email validation
        if "@" not in v or "." not in v.split("@")[1]:
            raise InvalidInputError("Invalid email format")
        return v.strip().lower()

    @field_validator("password_hash")
    @classmethod
    def password_hash_must_not_be_empty(cls, v: str) -> str:
        """Validate password hash is not empty."""
        if not v or not v.strip():
            raise InvalidInputError("Password hash cannot be empty")
        return v

    @classmethod
    async def create(cls, email: str, password: str) -> "User":
        """
        Create a new user with hashed password.
        
        Args:
            email: User email address
            password: Plain text password (will be hashed)
            
        Returns:
            Created User instance
            
        Raises:
            InvalidInputError: If email or password is invalid
            DatabaseOperationError: If user already exists or database error
        """
        # Check if user already exists
        existing_user = await cls.get_by_email(email)
        if existing_user:
            raise InvalidInputError(f"User with email {email} already exists")

        # Hash the password
        password_hash = hash_password(password)

        # Create user instance
        user = cls(
            email=email,
            password_hash=password_hash,
        )

        # Save to database
        await user.save()

        logger.info(f"Created new user: {email}")
        return user

    @classmethod
    async def get_by_email(cls, email: str) -> Optional["User"]:
        """
        Get user by email address.
        
        Args:
            email: Email address to search for
            
        Returns:
            User instance if found, None otherwise
        """
        try:
            email_lower = email.strip().lower()
            result = await repo_query(
                "SELECT * FROM user WHERE email = $email LIMIT 1",
                {"email": email_lower}
            )
            
            if result and len(result) > 0:
                return cls(**result[0])
            return None
        except Exception as e:
            logger.error(f"Error fetching user by email {email}: {str(e)}")
            logger.exception(e)
            raise DatabaseOperationError(e)

    def verify_password(self, password: str) -> bool:
        """
        Verify a password against this user's password hash.
        
        Args:
            password: Plain text password to verify
            
        Returns:
            True if password matches, False otherwise
        """
        return verify_password(password, self.password_hash)

    async def update_last_login(self) -> None:
        """Update the last_login timestamp."""
        self.last_login = datetime.now()
        await self.save()

