import unittest

import mock
import requests

import sms_plusserver


class SMSResponseTestCase(unittest.TestCase):
    """Tests for `SMSResponse` class"""

    def test_repr(self):
        response = sms_plusserver.SMSResponse(
            'REQUEST OK\nA = 42\nB = X Y\n C D = '
        )
        self.assertEqual(repr(response), '<SMSResponse [REQUEST OK]>')

    def test_empty_response_text(self):
        response = sms_plusserver.SMSResponse('')
        self.assertEqual(response.message, '')
        self.assertEqual(list(response.items()), [])

    def test_message_no_params(self):
        response = sms_plusserver.SMSResponse('ERROR')
        self.assertEqual(response.message, 'ERROR')
        self.assertEqual(list(response.items()), [])

    def test_message_and_params(self):
        response = sms_plusserver.SMSResponse(
            'REQUEST OK\nA = 42\nB = X Y\n C D = '
        )
        self.assertEqual(response.message, 'REQUEST OK')
        self.assertEqual(
            list(response.items()), [('A', '42'), ('B', 'X Y'), ('C D', '')]
        )

    def test_message_and_params_with_skipped_lines(self):
        response = sms_plusserver.SMSResponse(
            'REQUEST OK\nA = 42\nB\n\n C D = '
        )
        self.assertEqual(response.message, 'REQUEST OK')
        self.assertEqual(list(response.items()), [('A', '42'), ('C D', '')])

    def test_iter_empty(self):
        response = sms_plusserver.SMSResponse('Unauthorized')
        self.assertEqual([key for key in response], [])

    def test_iter_full(self):
        response = sms_plusserver.SMSResponse(
            'REQUEST OK\nA = 42\nB = X Y\n C D = '
        )
        self.assertEqual([key for key in response], ['A', 'B', 'C D'])

    def test_get_missing(self):
        response = sms_plusserver.SMSResponse(
            'REQUEST OK\nA = 42\nB = X Y\n C D = '
        )
        self.assertIsNone(response.get('E'))

    def test_get_missing_default(self):
        response = sms_plusserver.SMSResponse(
            'REQUEST OK\nA = 42\nB = X Y\n C D = '
        )
        self.assertEqual(response.get('E', default=''), '')

    def test_get_found(self):
        response = sms_plusserver.SMSResponse(
            'REQUEST OK\nA = 42\nB = X Y\n C D = '
        )
        self.assertEqual(response.get('A'), '42')

    def test_get_item_missing(self):
        response = sms_plusserver.SMSResponse(
            'REQUEST OK\nA = 42\nB = X Y\n C D = '
        )
        with self.assertRaises(KeyError):
            response['E']

    def test_get_item_found(self):
        response = sms_plusserver.SMSResponse(
            'REQUEST OK\nA = 42\nB = X Y\n C D = '
        )
        self.assertEqual(response['B'], 'X Y')

    def test_handle_id_missing(self):
        response = sms_plusserver.SMSResponse('REQUEST OK\n')
        self.assertIsNone(response.handle_id)

    def test_handle_id_found(self):
        response = sms_plusserver.SMSResponse(
            'REQUEST OK\nhandle = d41d8cd98f00b204e9800998ecf8427e'
        )
        self.assertEqual(
            response.handle_id, 'd41d8cd98f00b204e9800998ecf8427e'
        )

    def test_state_missing(self):
        response = sms_plusserver.SMSResponse('REQUEST OK\n')
        self.assertIsNone(response.state)

    def test_state_found(self):
        response = sms_plusserver.SMSResponse('REQUEST OK\nstate = arrived')
        self.assertEqual(response.state, 'arrived')

    def test_error_missing(self):
        response = sms_plusserver.SMSResponse('ERROR\n')
        self.assertIsNone(response.error)

    def test_error_found(self):
        response = sms_plusserver.SMSResponse(
            'ERROR\nerror = Something is wrong, please investigate!\n'
        )
        self.assertEqual(
            response.error, 'Something is wrong, please investigate!'
        )


class SMSServiceTestCase(unittest.TestCase):
    """Tests for `SMSService` class"""

    def test_repr(self):
        service = sms_plusserver.SMSService(
            username='user', password='pass', project='myproject'
        )
        self.assertEqual(repr(service), '<SMSService user @ myproject>')

        service = sms_plusserver.SMSService(username='user', password='pass')
        self.assertEqual(repr(service), '<SMSService user>')

    def test_default_service_attributes(self):
        self.assertEqual(
            sms_plusserver.default_service.put_url,
            sms_plusserver.SMSService.SMS_PUT_URL,
        )
        self.assertEqual(
            sms_plusserver.default_service.sms_state_url,
            sms_plusserver.SMSService.SMS_STATE_URL,
        )
        self.assertEqual(sms_plusserver.default_service.project, '')
        self.assertIsNone(sms_plusserver.default_service.username)
        self.assertIsNone(sms_plusserver.default_service.password)
        self.assertIsNone(sms_plusserver.default_service.orig)
        self.assertIsNone(sms_plusserver.default_service.encoding)
        self.assertIsNone(sms_plusserver.default_service.max_parts)
        self.assertIsNone(sms_plusserver.default_service.timeout)

    def test_init_default_attributes(self):
        service = sms_plusserver.SMSService()
        self.assertEqual(
            service.put_url, sms_plusserver.default_service.put_url
        )
        self.assertEqual(
            service.sms_state_url, sms_plusserver.default_service.sms_state_url
        )
        self.assertEqual(
            service.project, sms_plusserver.default_service.project
        )
        self.assertEqual(
            service.username, sms_plusserver.default_service.username
        )
        self.assertEqual(
            service.password, sms_plusserver.default_service.password
        )
        self.assertEqual(service.orig, sms_plusserver.default_service.orig)
        self.assertEqual(
            service.encoding, sms_plusserver.default_service.encoding
        )
        self.assertEqual(
            service.max_parts, sms_plusserver.default_service.max_parts
        )
        self.assertEqual(
            service.timeout, sms_plusserver.default_service.timeout
        )

    def test_init_custom_attributes(self):
        custom_put_url = 'http://localhost:8000/put.php'
        custom_sms_state_url = 'http://localhost:8000/sms-state.php'
        custom_project = 'TestProject'
        custom_username = 'johndoe'
        custom_password = 'admin.1'
        custom_orig = 'TEST'
        custom_encoding = 'utf-8'
        custom_max_parts = 3
        custom_timeout = 30

        service = sms_plusserver.SMSService(
            put_url=custom_put_url,
            sms_state_url=custom_sms_state_url,
            project=custom_project,
            username=custom_username,
            password=custom_password,
            orig=custom_orig,
            encoding=custom_encoding,
            max_parts=custom_max_parts,
            timeout=custom_timeout,
        )

        self.assertEqual(service.put_url, custom_put_url)
        self.assertEqual(service.sms_state_url, custom_sms_state_url)
        self.assertEqual(service.project, custom_project)
        self.assertEqual(service.username, custom_username)
        self.assertEqual(service.password, custom_password)
        self.assertEqual(service.orig, custom_orig)
        self.assertEqual(service.encoding, custom_encoding)
        self.assertEqual(service.max_parts, custom_max_parts)
        self.assertEqual(service.timeout, custom_timeout)

    def test_configure(self):
        custom_put_url = 'http://localhost:8000/put.php'
        custom_sms_state_url = 'http://localhost:8000/sms-state.php'
        custom_project = 'TestProject'
        custom_username = 'johndoe'
        custom_password = 'admin.1'
        custom_orig = 'TEST'
        custom_encoding = 'utf-8'
        custom_max_parts = 3
        custom_timeout = 30

        service = sms_plusserver.SMSService()
        service.configure(
            put_url=custom_put_url,
            sms_state_url=custom_sms_state_url,
            project=custom_project,
            username=custom_username,
            password=custom_password,
            orig=custom_orig,
            encoding=custom_encoding,
            max_parts=custom_max_parts,
            timeout=custom_timeout,
        )

        self.assertEqual(service.put_url, custom_put_url)
        self.assertEqual(service.sms_state_url, custom_sms_state_url)
        self.assertEqual(service.project, custom_project)
        self.assertEqual(service.username, custom_username)
        self.assertEqual(service.password, custom_password)
        self.assertEqual(service.orig, custom_orig)
        self.assertEqual(service.encoding, custom_encoding)
        self.assertEqual(service.max_parts, custom_max_parts)
        self.assertEqual(service.timeout, custom_timeout)

    # Tests for `put_sms` method:

    @mock.patch('sms_plusserver.requests.post')
    def test_put_sms_ok_default_params(self, mock_post):
        type(mock_post.return_value).text = mock.PropertyMock(
            return_value=(
                'REQUEST OK\nhandle = d41d8cd98f00b204e9800998ecf8427e'
            )
        )
        service = sms_plusserver.SMSService(
            username='user', password='pass', project='TESTPROJECT'
        )

        response = service.put_sms('+4911122233344', 'Hello!')

        mock_post.assert_called_once_with(
            sms_plusserver.SMSService.SMS_PUT_URL,
            {
                'dest': '+4911122233344',
                'data': 'Hello!',
                'debug': '0',
                'project': 'TESTPROJECT',
                'registered_delivery': '1',
            },
            auth=('user', 'pass'),
            timeout=None,
        )
        self.assertIsInstance(response, sms_plusserver.SMSResponse)
        self.assertEqual(response.message, 'REQUEST OK')
        self.assertEqual(
            response.handle_id, 'd41d8cd98f00b204e9800998ecf8427e'
        )

    @mock.patch('sms_plusserver.requests.post')
    def test_put_sms_ok_custom_params(self, mock_post):
        type(mock_post.return_value).text = mock.PropertyMock(
            return_value=(
                'REQUEST OK\nhandle = d41d8cd98f00b204e9800998ecf8427e'
            )
        )
        service = sms_plusserver.SMSService(
            username='user', password='pass', project='TESTPROJECT'
        )

        response = service.put_sms(
            '+4911122233344',
            'Hello!',
            orig='TEST',
            registered_delivery=False,
            debug=True,
            project='PROJECT2',
            encoding='utf-8',
            max_parts=3,
            timeout=30,
        )

        mock_post.assert_called_once_with(
            sms_plusserver.SMSService.SMS_PUT_URL,
            {
                'dest': '+4911122233344',
                'data': 'Hello!',
                'debug': '1',
                'project': 'PROJECT2',
                'registered_delivery': '0',
                'orig': 'TEST',
                'enc': 'utf-8',
                'maxparts': '3',
            },
            auth=('user', 'pass'),
            timeout=30,
        )
        self.assertIsInstance(response, sms_plusserver.SMSResponse)
        self.assertEqual(response.message, 'REQUEST OK')
        self.assertEqual(
            response.handle_id, 'd41d8cd98f00b204e9800998ecf8427e'
        )

    @mock.patch('sms_plusserver.requests.post')
    def test_put_sms_error_missing_credentials(self, mock_post):
        service = sms_plusserver.SMSService()

        with self.assertRaises(sms_plusserver.ConfigurationError):
            service.put_sms('+4911122233344', 'Hello!')

        mock_post.assert_not_called()

    @mock.patch('sms_plusserver.requests.post')
    def test_put_sms_error_response(self, mock_post):
        type(mock_post.return_value).text = mock.PropertyMock(
            return_value='ERROR\nerror = Something is wrong'
        )
        service = sms_plusserver.SMSService(
            username='user', password='pass', project='TESTPROJECT'
        )

        with self.assertRaises(sms_plusserver.RequestError) as raised:
            service.put_sms('+4911122233344', 'Hello!')

        mock_post.assert_called_once_with(
            sms_plusserver.SMSService.SMS_PUT_URL,
            {
                'dest': '+4911122233344',
                'data': 'Hello!',
                'debug': '0',
                'project': 'TESTPROJECT',
                'registered_delivery': '1',
            },
            auth=('user', 'pass'),
            timeout=None,
        )
        self.assertEqual(str(raised.exception), 'Something is wrong')

    @mock.patch(
        'sms_plusserver.requests.post', side_effect=requests.ConnectTimeout
    )
    def test_put_sms_error_network(self, mock_post):
        service = sms_plusserver.SMSService(
            username='user', password='pass', project='TESTPROJECT'
        )

        with self.assertRaises(sms_plusserver.CommunicationError) as raised:
            service.put_sms('+4911122233344', 'Hello!')

        mock_post.assert_called_once_with(
            sms_plusserver.SMSService.SMS_PUT_URL,
            {
                'dest': '+4911122233344',
                'data': 'Hello!',
                'debug': '0',
                'project': 'TESTPROJECT',
                'registered_delivery': '1',
            },
            auth=('user', 'pass'),
            timeout=None,
        )
        self.assertIsInstance(
            raised.exception.original_exception, requests.ConnectTimeout
        )

    @mock.patch('sms_plusserver.requests.post')
    def test_put_sms_error_http(self, mock_post):
        type(mock_post.return_value).text = mock.PropertyMock(
            return_value='Something is wrong'
        )
        type(mock_post.return_value).raise_for_status = mock.MagicMock(
            side_effect=requests.HTTPError
        )
        service = sms_plusserver.SMSService(
            username='user', password='pass', project='TESTPROJECT'
        )

        with self.assertRaises(sms_plusserver.RequestError) as raised:
            service.put_sms('+4911122233344', 'Hello!')

        mock_post.assert_called_once_with(
            sms_plusserver.SMSService.SMS_PUT_URL,
            {
                'dest': '+4911122233344',
                'data': 'Hello!',
                'debug': '0',
                'project': 'TESTPROJECT',
                'registered_delivery': '1',
            },
            auth=('user', 'pass'),
            timeout=None,
        )
        self.assertIsInstance(
            raised.exception.original_exception, requests.HTTPError
        )

    @mock.patch(
        'sms_plusserver.requests.post', side_effect=requests.ConnectTimeout
    )
    def test_put_sms_error_fail_silently(self, mock_post):
        type(mock_post.return_value).text = mock.PropertyMock(
            return_value='REQUEST ERROR\nerror = Something is wrong'
        )
        service = sms_plusserver.SMSService(
            username='user', password='pass', project='TESTPROJECT'
        )

        response = service.put_sms(
            '+4911122233344', 'Hello!', fail_silently=True
        )

        mock_post.assert_called_once_with(
            sms_plusserver.SMSService.SMS_PUT_URL,
            {
                'dest': '+4911122233344',
                'data': 'Hello!',
                'debug': '0',
                'project': 'TESTPROJECT',
                'registered_delivery': '1',
            },
            auth=('user', 'pass'),
            timeout=None,
        )
        self.assertIsNone(response)

    # Tests for `check_sms_state` method:

    @mock.patch('sms_plusserver.requests.post')
    def test_check_sms_state_ok_default_params(self, mock_post):
        type(mock_post.return_value).text = mock.PropertyMock(
            return_value='REQUEST OK\nstate = arrived'
        )
        service = sms_plusserver.SMSService(
            username='user', password='pass', project='TESTPROJECT'
        )

        response = service.check_sms_state('d41d8cd98f00b204e9800998ecf8427e')

        mock_post.assert_called_once_with(
            sms_plusserver.SMSService.SMS_STATE_URL,
            {'handle': 'd41d8cd98f00b204e9800998ecf8427e',},
            auth=('user', 'pass'),
            timeout=None,
        )
        self.assertIsInstance(response, sms_plusserver.SMSResponse)
        self.assertEqual(response.message, 'REQUEST OK')
        self.assertEqual(response.state, 'arrived')

    @mock.patch('sms_plusserver.requests.post')
    def test_check_sms_state_ok_custom_params(self, mock_post):
        type(mock_post.return_value).text = mock.PropertyMock(
            return_value='REQUEST OK\nstate = arrived'
        )
        service = sms_plusserver.SMSService(
            username='user', password='pass', project='TESTPROJECT'
        )

        response = service.check_sms_state(
            'd41d8cd98f00b204e9800998ecf8427e', timeout=30
        )

        mock_post.assert_called_once_with(
            sms_plusserver.SMSService.SMS_STATE_URL,
            {'handle': 'd41d8cd98f00b204e9800998ecf8427e',},
            auth=('user', 'pass'),
            timeout=30,
        )
        self.assertIsInstance(response, sms_plusserver.SMSResponse)
        self.assertEqual(response.message, 'REQUEST OK')
        self.assertEqual(response.state, 'arrived')

    @mock.patch('sms_plusserver.requests.post')
    def test_check_sms_state_error_missing_credentials(self, mock_post):
        service = sms_plusserver.SMSService()

        with self.assertRaises(sms_plusserver.ConfigurationError):
            service.check_sms_state('d41d8cd98f00b204e9800998ecf8427e')

        mock_post.assert_not_called()

    @mock.patch('sms_plusserver.requests.post')
    def test_check_sms_state_error_missing_handle_id(self, mock_post):
        service = sms_plusserver.SMSService(username='user', password='pass')

        with self.assertRaises(sms_plusserver.ValidationError):
            service.check_sms_state(None)

        mock_post.assert_not_called()

    @mock.patch('sms_plusserver.requests.post')
    def test_check_sms_state_error_response(self, mock_post):
        type(mock_post.return_value).text = mock.PropertyMock(
            return_value='ERROR\nerror = Something is wrong'
        )
        service = sms_plusserver.SMSService(
            username='user', password='pass', project='TESTPROJECT'
        )

        with self.assertRaises(sms_plusserver.RequestError) as raised:
            service.check_sms_state('unknownhandle')

        mock_post.assert_called_once_with(
            sms_plusserver.SMSService.SMS_STATE_URL,
            {'handle': 'unknownhandle',},
            auth=('user', 'pass'),
            timeout=None,
        )
        self.assertEqual(str(raised.exception), 'Something is wrong')

    @mock.patch(
        'sms_plusserver.requests.post', side_effect=requests.ConnectTimeout
    )
    def test_check_sms_state_error_network(self, mock_post):
        service = sms_plusserver.SMSService(
            username='user', password='pass', project='TESTPROJECT'
        )

        with self.assertRaises(sms_plusserver.CommunicationError) as raised:
            service.check_sms_state('d41d8cd98f00b204e9800998ecf8427e')

        mock_post.assert_called_once_with(
            sms_plusserver.SMSService.SMS_STATE_URL,
            {'handle': 'd41d8cd98f00b204e9800998ecf8427e',},
            auth=('user', 'pass'),
            timeout=None,
        )
        self.assertIsInstance(
            raised.exception.original_exception, requests.ConnectTimeout
        )

    @mock.patch('sms_plusserver.requests.post')
    def test_check_sms_state_error_http(self, mock_post):
        type(mock_post.return_value).text = mock.PropertyMock(
            return_value='Something is wrong'
        )
        type(mock_post.return_value).raise_for_status = mock.MagicMock(
            side_effect=requests.HTTPError
        )
        service = sms_plusserver.SMSService(
            username='user', password='pass', project='TESTPROJECT'
        )

        with self.assertRaises(sms_plusserver.RequestError) as raised:
            service.check_sms_state('d41d8cd98f00b204e9800998ecf8427e')

        mock_post.assert_called_once_with(
            sms_plusserver.SMSService.SMS_STATE_URL,
            {'handle': 'd41d8cd98f00b204e9800998ecf8427e',},
            auth=('user', 'pass'),
            timeout=None,
        )
        self.assertIsInstance(
            raised.exception.original_exception, requests.HTTPError
        )

    @mock.patch(
        'sms_plusserver.requests.post', side_effect=requests.ConnectTimeout
    )
    def test_check_sms_state_fail_silently(self, mock_post):
        type(mock_post.return_value).text = mock.PropertyMock(
            return_value='REQUEST ERROR\nerror = Something is wrong'
        )
        service = sms_plusserver.SMSService(
            username='user', password='pass', project='TESTPROJECT'
        )

        response = service.check_sms_state(
            'd41d8cd98f00b204e9800998ecf8427e', fail_silently=True
        )

        mock_post.assert_called_once_with(
            sms_plusserver.SMSService.SMS_STATE_URL,
            {'handle': 'd41d8cd98f00b204e9800998ecf8427e',},
            auth=('user', 'pass'),
            timeout=None,
        )
        self.assertIsNone(response)

    # Tests for `send` method:

    @mock.patch(
        'sms_plusserver.SMSService.put_sms',
        return_value=sms_plusserver.SMSResponse(
            'REQUEST OK\nhandle = d41d8cd98f00b204e9800998ecf8427e'
        ),
    )
    def test_send_ok_default_params(self, mock_put_sms):
        service = sms_plusserver.SMSService()
        sms = sms_plusserver.SMS('+4911122233344', 'Hello!')

        handle_id = service.send(sms)

        mock_put_sms.assert_called_once_with(
            destination='+4911122233344',
            text='Hello!',
            orig=None,
            registered_delivery=True,
            debug=False,
            project=None,
            encoding=None,
            max_parts=None,
            timeout=None,
            fail_silently=False,
        )
        self.assertEqual(handle_id, 'd41d8cd98f00b204e9800998ecf8427e')
        self.assertIsInstance(sms.put_response, sms_plusserver.SMSResponse)

    @mock.patch(
        'sms_plusserver.SMSService.put_sms',
        return_value=sms_plusserver.SMSResponse('REQUEST OK\n'),
    )
    def test_send_ok_custom_params(self, mock_put_sms):
        service = sms_plusserver.SMSService()
        sms = sms_plusserver.SMS(
            '+4911122233344',
            'Hello!',
            orig='TEST',
            registered_delivery=False,
            debug=True,
            project='PROJECT2',
            encoding='utf-8',
            max_parts=3,
        )

        success = service.send(sms, timeout=30, fail_silently=True)

        mock_put_sms.assert_called_once_with(
            destination='+4911122233344',
            text='Hello!',
            orig='TEST',
            registered_delivery=False,
            debug=True,
            project='PROJECT2',
            encoding='utf-8',
            max_parts=3,
            timeout=30,
            fail_silently=True,
        )
        self.assertTrue(success)
        self.assertIsInstance(sms.put_response, sms_plusserver.SMSResponse)

    @mock.patch(
        'sms_plusserver.SMSService.put_sms',
        side_effect=sms_plusserver.RequestError('Error occurred'),
    )
    def test_send_service_error(self, mock_put_sms):
        service = sms_plusserver.SMSService()
        sms = sms_plusserver.SMS('+4911122233344', 'Hello!')

        with self.assertRaises(sms_plusserver.RequestError):
            service.send(sms)

        mock_put_sms.assert_called_once_with(
            destination='+4911122233344',
            text='Hello!',
            orig=None,
            registered_delivery=True,
            debug=False,
            project=None,
            encoding=None,
            max_parts=None,
            timeout=None,
            fail_silently=False,
        )
        self.assertIsNone(sms.put_response)

    # Tests for `check_state` method:

    @mock.patch(
        'sms_plusserver.SMSService.check_sms_state',
        return_value=sms_plusserver.SMSResponse('REQUEST OK\nstate = arrived'),
    )
    def test_check_state_ok_default_params(self, mock_check_sms_state):
        service = sms_plusserver.SMSService()
        sms = sms_plusserver.SMS('+4911122233344', 'Hello!')
        sms.put_response = sms_plusserver.SMSResponse(
            'REQUEST OK\nhandle = d41d8cd98f00b204e9800998ecf8427e'
        )

        state = service.check_state(sms)

        mock_check_sms_state.assert_called_once_with(
            handle_id='d41d8cd98f00b204e9800998ecf8427e',
            timeout=None,
            fail_silently=False,
        )
        self.assertEqual(state, 'arrived')
        self.assertIsInstance(sms.state_response, sms_plusserver.SMSResponse)

    @mock.patch(
        'sms_plusserver.SMSService.check_sms_state',
        return_value=sms_plusserver.SMSResponse('REQUEST OK\nstate = arrived'),
    )
    def test_check_state_ok_custom_params(self, mock_check_sms_state):
        service = sms_plusserver.SMSService()
        sms = sms_plusserver.SMS('+4911122233344', 'Hello!')
        sms.put_response = sms_plusserver.SMSResponse(
            'REQUEST OK\nhandle = d41d8cd98f00b204e9800998ecf8427e'
        )

        state = service.check_state(sms, timeout=30, fail_silently=True)

        mock_check_sms_state.assert_called_once_with(
            handle_id='d41d8cd98f00b204e9800998ecf8427e',
            timeout=30,
            fail_silently=True,
        )
        self.assertEqual(state, 'arrived')
        self.assertIsInstance(sms.state_response, sms_plusserver.SMSResponse)

    @mock.patch(
        'sms_plusserver.SMSService.check_sms_state',
        side_effect=sms_plusserver.RequestError('Error occurred'),
    )
    def test_check_state_service_error(self, mock_check_sms_state):
        service = sms_plusserver.SMSService()
        sms = sms_plusserver.SMS('+4911122233344', 'Hello!')
        sms.put_response = sms_plusserver.SMSResponse(
            'REQUEST OK\nhandle = d41d8cd98f00b204e9800998ecf8427e'
        )

        with self.assertRaises(sms_plusserver.RequestError):
            service.check_state(sms)

        mock_check_sms_state.assert_called_once_with(
            handle_id='d41d8cd98f00b204e9800998ecf8427e',
            timeout=None,
            fail_silently=False,
        )
        self.assertIsNone(sms.state_response)


class SMSTestCase(unittest.TestCase):
    """Tests for `SMS` class"""

    def test_init_default_attributes(self):
        destination = '+4911122233344'
        text = 'Hello!'

        sms = sms_plusserver.SMS(destination, text)

        self.assertEqual(sms.destination, destination)
        self.assertEqual(sms.text, text)
        self.assertIsNone(sms.orig)
        self.assertTrue(sms.registered_delivery)
        self.assertFalse(sms.debug)
        self.assertIsNone(sms.project)
        self.assertIsNone(sms.encoding)
        self.assertIsNone(sms.max_parts)

    def test_init_custom_attributes(self):
        destination = '+4911122233344'
        text = 'Hello!'
        custom_orig = 'TEST'
        custom_registered_delivery = False
        custom_debug = True
        custom_project = 'TestProject'
        custom_encoding = 'utf-8'
        custom_max_parts = 3

        sms = sms_plusserver.SMS(
            destination,
            text,
            orig=custom_orig,
            registered_delivery=custom_registered_delivery,
            debug=custom_debug,
            project=custom_project,
            encoding=custom_encoding,
            max_parts=custom_max_parts,
        )

        self.assertEqual(sms.destination, destination)
        self.assertEqual(sms.text, text)
        self.assertEqual(sms.orig, custom_orig)
        self.assertEqual(sms.registered_delivery, custom_registered_delivery)
        self.assertEqual(sms.debug, custom_debug)
        self.assertEqual(sms.project, custom_project)
        self.assertEqual(sms.encoding, custom_encoding)
        self.assertEqual(sms.max_parts, custom_max_parts)

    def test_repr(self):
        sms = sms_plusserver.SMS('+4911122233344', 'Hello!')
        self.assertEqual(repr(sms), '<SMS +4911122233344>')

        sms.put_response = sms_plusserver.SMSResponse(
            'REQUEST OK\nhandle = d41d8cd98f00b204e9800998ecf8427e'
        )
        self.assertEqual(
            repr(sms),
            '<SMS +4911122233344 [d41d8cd98f00b204e9800998ecf8427e]>',
        )

        sms.state_response = sms_plusserver.SMSResponse(
            'REQUEST OK\nstate = processed'
        )
        self.assertEqual(
            repr(sms),
            '<SMS +4911122233344 [d41d8cd98f00b204e9800998ecf8427e] processed>',
        )

    # Tests for `send` method:

    @mock.patch('sms_plusserver.SMSService.send')
    def test_send_default_parameters(self, mock_send):
        sms = sms_plusserver.SMS('+4911122233344', 'Hello!')

        sms.send()

        mock_send.assert_called_once_with(
            sms, timeout=None, fail_silently=False
        )

    @mock.patch('sms_plusserver.SMSService.send')
    def test_send_custom_parameters(self, mock_send):
        sms = sms_plusserver.SMS('+4911122233344', 'Hello!')

        sms.send(timeout=30, fail_silently=True)

        mock_send.assert_called_once_with(sms, timeout=30, fail_silently=True)

    @mock.patch('sms_plusserver.SMSService.send')
    def test_send_custom_service(self, mock_send):
        mock_service = mock.MagicMock()
        sms = sms_plusserver.SMS('+4911122233344', 'Hello!')

        sms.send(service=mock_service)

        mock_service.send.assert_called_once_with(
            sms, timeout=None, fail_silently=False
        )
        mock_send.assert_not_called()

    # Tests for `check_state` method:

    @mock.patch('sms_plusserver.SMSService.check_state')
    def test_check_state_default_parameters(self, mock_check_state):
        sms = sms_plusserver.SMS('+4911122233344', 'Hello!')

        sms.check_state()

        mock_check_state.assert_called_once_with(
            sms, wait=False, timeout=None, fail_silently=False
        )

    @mock.patch('sms_plusserver.SMSService.check_state')
    def test_check_state_custom_parameters(self, mock_check_state):
        sms = sms_plusserver.SMS('+4911122233344', 'Hello!')

        sms.check_state(wait=True, timeout=30, fail_silently=True)

        mock_check_state.assert_called_once_with(
            sms, wait=True, timeout=30, fail_silently=True
        )

    @mock.patch('sms_plusserver.SMSService.check_state')
    def test_check_state_custom_service(self, mock_check_state):
        mock_service = mock.MagicMock()
        sms = sms_plusserver.SMS('+4911122233344', 'Hello!')

        sms.check_state(service=mock_service)

        mock_service.check_state.assert_called_once_with(
            sms, wait=False, timeout=None, fail_silently=False
        )
        mock_check_state.assert_not_called()

    # Other tests:

    def test_handle_id_no_put_response(self):
        sms = sms_plusserver.SMS('+4911122233344', 'Hello!')
        self.assertIsNone(sms.handle_id)

    def test_handle_id_with_put_response(self):
        sms = sms_plusserver.SMS('+4911122233344', 'Hello!')
        sms.put_response = sms_plusserver.SMSResponse(
            'REQUEST OK\nhandle = d41d8cd98f00b204e9800998ecf8427e'
        )
        self.assertEqual(sms.handle_id, 'd41d8cd98f00b204e9800998ecf8427e')

    def test_state_no_state_response(self):
        sms = sms_plusserver.SMS('+4911122233344', 'Hello!')
        self.assertIsNone(sms.state)

    def test_state_with_put_response(self):
        sms = sms_plusserver.SMS('+4911122233344', 'Hello!')
        sms.put_response = sms_plusserver.SMSResponse(
            'REQUEST OK\nhandle = d41d8cd98f00b204e9800998ecf8427e'
        )
        self.assertIsNone(sms.state)  # No 'state' found in put response

    def test_state_with_put_and_state_response(self):
        sms = sms_plusserver.SMS('+4911122233344', 'Hello!')
        sms.put_response = sms_plusserver.SMSResponse(
            'REQUEST OK\nhandle = d41d8cd98f00b204e9800998ecf8427e'
        )
        sms.state_response = sms_plusserver.SMSResponse(
            'REQUEST OK\nstate = arrived\n'
        )
        self.assertEqual(sms.state, 'arrived')


class FunctionsTestCase(unittest.TestCase):
    """Tests for top-level functions:
    `send_sms`, `check_sms_state`, `configure`
    """

    # Tests for `send_sms`:

    @mock.patch(
        'sms_plusserver.SMSService.put_sms',
        return_value=sms_plusserver.SMSResponse(
            'REQUEST OK\nhandle = d41d8cd98f00b204e9800998ecf8427e'
        ),
    )
    def test_send_sms_default_params(self, mock_put_sms):
        handle_id = sms_plusserver.send_sms('+4911122233344', 'Hello!')

        mock_put_sms.assert_called_once_with(
            destination='+4911122233344',
            text='Hello!',
            orig=None,
            registered_delivery=True,
            debug=False,
            project=None,
            encoding=None,
            max_parts=None,
            timeout=None,
            fail_silently=False,
        )
        self.assertEqual(handle_id, 'd41d8cd98f00b204e9800998ecf8427e')

    @mock.patch(
        'sms_plusserver.SMSService.put_sms',
        return_value=sms_plusserver.SMSResponse('REQUEST OK\n'),
    )
    def test_send_sms_custom_params(self, mock_put_sms):
        success = sms_plusserver.send_sms(
            '+4911122233344',
            'Hello!',
            orig='TEST',
            registered_delivery=False,
            debug=True,
            project='PROJECT2',
            encoding='utf-8',
            max_parts=3,
            timeout=30,
            fail_silently=True,
        )

        mock_put_sms.assert_called_once_with(
            destination='+4911122233344',
            text='Hello!',
            orig='TEST',
            registered_delivery=False,
            debug=True,
            project='PROJECT2',
            encoding='utf-8',
            max_parts=3,
            timeout=30,
            fail_silently=True,
        )
        self.assertTrue(success)

    def test_send_sms_custom_service(self):
        mock_service = mock.MagicMock()
        sms_plusserver.send_sms(
            '+4911122233344', 'Hello!', service=mock_service
        )
        mock_service.send.assert_called_once()

    # Tests for `check_sms_state`:

    @mock.patch(
        'sms_plusserver.SMSService.check_sms_state',
        return_value=sms_plusserver.SMSResponse('REQUEST OK\nstate = arrived'),
    )
    def test_check_sms_state_default_params(self, mock_check_sms_state):
        state = sms_plusserver.check_sms_state(
            'd41d8cd98f00b204e9800998ecf8427e'
        )

        mock_check_sms_state.assert_called_once_with(
            'd41d8cd98f00b204e9800998ecf8427e',
            timeout=None,
            fail_silently=False,
        )
        self.assertEqual(state, 'arrived')

    @mock.patch(
        'sms_plusserver.SMSService.check_sms_state',
        return_value=sms_plusserver.SMSResponse('REQUEST OK\nstate = arrived'),
    )
    def test_check_sms_state_custom_params(self, mock_check_sms_state):
        state = sms_plusserver.check_sms_state(
            'd41d8cd98f00b204e9800998ecf8427e', timeout=30, fail_silently=True
        )

        mock_check_sms_state.assert_called_once_with(
            'd41d8cd98f00b204e9800998ecf8427e', timeout=30, fail_silently=True
        )
        self.assertEqual(state, 'arrived')

    def test_check_sms_state_custom_service(self):
        mock_service = mock.MagicMock()
        sms_plusserver.check_sms_state(
            'd41d8cd98f00b204e9800998ecf8427e', service=mock_service
        )
        mock_service.check_sms_state.assert_called_once()

    # Tests for `wait_until_arrived`:

    @mock.patch(
        'sms_plusserver.SMSService.check_sms_state',
        return_value=sms_plusserver.SMSResponse('REQUEST OK\nstate = arrived'),
    )
    def test_wait_until_arrived_default_params(self, mock_check_sms_state):
        state = sms_plusserver.wait_until_arrived(
            'd41d8cd98f00b204e9800998ecf8427e'
        )

        mock_check_sms_state.assert_called_once_with(
            'd41d8cd98f00b204e9800998ecf8427e',
            timeout=None,
            fail_silently=False,
        )
        self.assertEqual(state, 'arrived')

    @mock.patch(
        'sms_plusserver.SMSService.check_sms_state',
        return_value=sms_plusserver.SMSResponse('REQUEST OK\nstate = arrived'),
    )
    def test_wait_until_arrived_custom_params(self, mock_check_sms_state):
        state = sms_plusserver.wait_until_arrived(
            'd41d8cd98f00b204e9800998ecf8427e', timeout=30, fail_silently=True
        )

        mock_check_sms_state.assert_called_once_with(
            'd41d8cd98f00b204e9800998ecf8427e',
            timeout=30,
            fail_silently=False,  # this param is not propagated
        )
        self.assertEqual(state, 'arrived')

    def test_wait_until_arrived_custom_service(self):
        mock_service = mock.MagicMock()
        sms_plusserver.wait_until_arrived(
            'd41d8cd98f00b204e9800998ecf8427e', service=mock_service
        )
        mock_service.wait_until_arrived.assert_called_once()

    # Tests for `configure`:

    @mock.patch('sms_plusserver.default_service.configure')
    def test_configure(self, mock_configure):
        sms_plusserver.configure(username='user', password='pass')
        mock_configure.assert_called_with(username='user', password='pass')
