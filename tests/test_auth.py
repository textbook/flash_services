from flash_services.auth import BasicAuthHeaderMixin
from flash_services.core import Service


class BasicAuthParent(BasicAuthHeaderMixin, Service):
    def update(self): pass
    def format_data(self, data): pass


def test_basic_auth():
    service = BasicAuthParent(username='username', password='password')
    assert service.headers['Authorization'] == 'Basic dXNlcm5hbWU6cGFzc3dvcmQ='
