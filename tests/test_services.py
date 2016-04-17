from unittest import mock

from flash_services import define_services, SERVICES


@mock.patch('flash_services.uuid4')
def test_define_services(uuid4):
    mock_service = mock.MagicMock()
    with mock.patch.dict(SERVICES, {'bar': mock_service}, clear=True):

        result = define_services([{'name': 'bar'}, {'name': 'baz'}])

    uuid4.assert_called_once_with()
    assert result == {uuid4().hex: mock_service.from_config.return_value}
