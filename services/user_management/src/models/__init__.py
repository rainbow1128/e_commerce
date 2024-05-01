# following models will be referenced by Django's lazy initialization,
# which limits the model path to be <APP_LABEL>.<MODEL_NAME>
# any hierarchical package between <APP_LABEL> and <MODEL_NAME> is NOT allowed
# (Django cannot recognize that)
from .auth import LoginAccount
from .base import GenericUserProfile, GenericUserAppliedRole, EmailAddress
