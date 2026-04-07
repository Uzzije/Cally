from __future__ import annotations

from django.contrib.auth.models import User

AuthenticatedUser = User
"""Type alias for the project user model.

Used to annotate service method parameters instead of leaving ``user``
untyped.  Points to the concrete ``auth.User`` model so django-stubs
can validate ORM lookups and attribute access.

If the project switches to a custom user model in the future, update
this alias to point at the new model class.
"""
