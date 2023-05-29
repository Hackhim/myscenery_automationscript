import os
from pyrtable.record import APIKeyFromSecretsFileMixin, BaseRecord

BASE_ID = os.getenv("BASE_ID")


class Base(APIKeyFromSecretsFileMixin, BaseRecord):
    class Meta:
        base_id = BASE_ID

    @classmethod
    def get_all(cls):
        return cls.objects.all()
