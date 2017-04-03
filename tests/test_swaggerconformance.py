import logging
import unittest
import re
import os.path as osp

import responses

import swaggerconformance
import swaggerconformance.template
import swaggerconformance.client

TEST_SCHEMA_DIR = osp.relpath(osp.join(osp.dirname(osp.realpath(__file__)),
                                       'test_schemas/'))
TEST_SCHEMA_PATH = osp.join(TEST_SCHEMA_DIR, 'test_schema.json')
FULL_PUT_SCHEMA_PATH = osp.join(TEST_SCHEMA_DIR, 'full_put_schema.json')
ALL_CONSTRAINTS_SCHEMA_PATH = osp.join(TEST_SCHEMA_DIR,
                                       'all_constraints_schema.json')
PETSTORE_SCHEMA_PATH = osp.join(TEST_SCHEMA_DIR, 'petstore.json')
UBER_SCHEMA_PATH = osp.join(TEST_SCHEMA_DIR, 'uber.json')
SCHEMA_URL_BASE = 'http://127.0.0.1:5000/api'
CONTENT_TYPE_JSON = 'application/json'

def respond_to_method(method, path, response_json=None, status=200):
    url_re = re.compile(SCHEMA_URL_BASE + path + '$')
    responses.add(method, url_re,
                  json=response_json, status=status,
                  content_type=CONTENT_TYPE_JSON)

def respond_to_get(path, response_json=None, status=200):
    respond_to_method(responses.GET, path, response_json, status)

def respond_to_post(path, response_json=None, status=200):
    respond_to_method(responses.POST, path, response_json, status)

def respond_to_put(path, response_json=None, status=200):
    respond_to_method(responses.PUT, path, response_json, status)

def respond_to_delete(path, response_json=None, status=200):
    respond_to_method(responses.DELETE, path, response_json, status)


class APITemplateTestCase(unittest.TestCase):

    def setUp(self):
        self.client = swaggerconformance.client.SwaggerClient(TEST_SCHEMA_PATH)

    def tearDown(self):
        # No teardown of test fixtures required.
        pass

    def test_schema_parse(self):
        api_template = swaggerconformance.template.APITemplate(self.client)
        expected_endpoints = {'/schema', '/apps', '/apps/{appid}'}
        self.assertSetEqual(set(api_template.endpoints.keys()),
                            expected_endpoints)

    @responses.activate
    def test_endpoint_manually(self):
        api_template = swaggerconformance.template.APITemplate(self.client)

        # Find the template GET operation on the /apps/{appid} endpoint.
        app_id_get_op = None
        for operation_template in api_template.template_operations():
            if (operation_template.operation.method == 'get' and
                    operation_template.operation.path == '/apps/{appid}'):
                self.assertIsNone(app_id_get_op)
                app_id_get_op = operation_template
        self.assertIsNotNone(app_id_get_op)

        # The operation takes one parameter, 'appid', which is a string.
        self.assertEqual(list(app_id_get_op.parameters.keys()), ['appid'])
        self.assertEqual(app_id_get_op.parameters['appid'].type, 'string')

        # Send an example parameter in to the endpoint manually, catch the
        # request, and respond.
        params = {'appid': 'test_string'}
        respond_to_get('/apps/test_string', response_json={}, status=404)
        result = self.client.request(app_id_get_op, params)
        self.assertEqual(result.status, 404)


class ParameterTypesTestCase(unittest.TestCase):

    @responses.activate
    def test_full_put(self):
        # Handle all the basic endpoints.
        respond_to_get('/schema')
        respond_to_get('/example')
        respond_to_delete('/example', status=204)
        respond_to_put(r'/example/-?\d+', status=204)

        # Now just kick off the validation process.
        swaggerconformance.validate_schema(FULL_PUT_SCHEMA_PATH)

    @responses.activate
    def test_all_constraints(self):
        # Handle all the basic endpoints.
        respond_to_get('/schema')
        respond_to_put(r'/example/-?\d+', status=204)

        # Now just kick off the validation process.
        swaggerconformance.validate_schema(ALL_CONSTRAINTS_SCHEMA_PATH)


class ExternalExamplesTestCase(unittest.TestCase):

    @responses.activate
    def test_swaggerio_petstore(self):
        # Example responses matching the required models.
        pet = {"id": 0,
               "category": {"id": 0, "name": "string"},
               "name": "doggie",
               "photoUrls": ["string"],
               "tags": [{"id": 0, "name": "string"}],
               "status": "available"}
        pets = [pet]
        inventory = {"additionalProp1": 0, "additionalProp2": 0}
        order = {"id": 0,
                 "petId": 0,
                 "quantity": 0,
                 "shipDate": "2017-03-21T23:13:44.949Z",
                 "status": "placed",
                 "complete": True}
        api_response = {"code": 0, "type": "string", "message": "string"}
        user = {"id": 0,
                "username": "string",
                "firstName": "string",
                "lastName": "string",
                "email": "string",
                "password": "string",
                "phone": "string",
                "userStatus": 0}

        # Handle all the basic endpoints.
        respond_to_get('/pet')
        respond_to_post('/pet')
        respond_to_put('/pet')
        respond_to_get(r'/pet/-?\d+', response_json=pet)
        respond_to_delete(r'/pet/-?\d+')
        respond_to_post(r'/pet/-?\d+', response_json=api_response)
        respond_to_post(r'/pet/-?\d+/uploadImage', response_json=api_response)
        respond_to_get('/pet/findByStatus', response_json=pets)
        respond_to_get(r'/pet/findByStatus\?status=.*', response_json=pets)
        respond_to_get('/pet/findByTags', response_json=pets)
        respond_to_get(r'/pet/findByTags\?tags=.*', response_json=pets)
        respond_to_get('/store')
        respond_to_get('/store/inventory', response_json=inventory)
        respond_to_post('/store/order', response_json=order)
        respond_to_get(r'/store/order/-?\d+', response_json=order)
        respond_to_delete(r'/store/order/-?\d+')
        respond_to_get('/user')
        respond_to_post('/user')
        respond_to_delete('/user')
        respond_to_get(r'/user/(?!login).+', response_json=user)
        respond_to_put(r'/user/(?!login).+')
        respond_to_delete(r'/user/(?!login).+')
        respond_to_get(r'/user/login\?username=.*&password=.*',
                       response_json="example")
        respond_to_get('/user/logout')
        respond_to_post('/user/createWithArray')
        respond_to_post('/user/createWithList')
        respond_to_put(r'/example/-?\d+')

        # Now just kick off the validation process.
        swaggerconformance.validate_schema(PETSTORE_SCHEMA_PATH)

    @responses.activate
    def test_openapi_uber(self):
        profile = {"first_name": "steve",
                   "last_name": "stevenson",
                   "email": "example@stevemail.com",
                   "picture": "http://steve.com/stevepic.png",
                   "promo_code": "12341234"}
        activities = {"offset": 123,
                      "limit": 99,
                      "count": 432,
                      "history": [{"uuid": 9876543210}]}
        product = {"product_id": "example",
                   "description": "it's a product",
                   "display_name": "bestproductno1",
                   "capacity": "4 hippos",
                   "image": "http://hippotransports.com/hippocar.png"}
        products = [product]
        price_estimate = {"product_id": "example",
                          "currency_code": "gbp",
                          "display_name": "it's a product",
                          "estimate": "123.50",
                          "low_estimate": 123,
                          "high_estimate": 124,
                          "surge_multiplier": 22.2}
        price_estimates = [price_estimate]

        # Handle all the basic endpoints.
        respond_to_get(r'/estimates/price\?.*', response_json=price_estimates)
        respond_to_get(r'/estimates/time\?.*', response_json=products)
        respond_to_get(r'/history\?.*', response_json=activities)
        respond_to_get('/me', response_json=profile)
        respond_to_get(r'/products\?.*', response_json=products)

        # Now just kick off the validation process.
        swaggerconformance.validate_schema(UBER_SCHEMA_PATH)


if __name__ == '__main__':
    LOG_FORMAT = '%(asctime)s:%(levelname)-7s:%(funcName)s:%(message)s'
    logging.basicConfig(format=LOG_FORMAT, level=logging.DEBUG)
    unittest.main()