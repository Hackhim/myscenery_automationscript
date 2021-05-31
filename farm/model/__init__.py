from pyrtable.record import APIKeyFromSecretsFileMixin, BaseRecord


TESTING = False
if TESTING:
    BASE_ID = 'appcXZIDFOZBXkFvz'
else:
    BASE_ID = 'appTPuSS21Awvjqed'


class Base(APIKeyFromSecretsFileMixin, BaseRecord):
    class Meta:
        base_id = BASE_ID
    
    @classmethod
    def get_all(cls):
        return cls.objects.all()


