import logging


log = logging.getLogger(__name__)


class IntegerTemplate:
    """Template for an integer value with constraints."""

    def __init__(self):
        pass


class StringTemplate:
    """Template for a string value with constraints."""

    def __init__(self):
        pass


class FloatTemplate:
    """Template for a floating point value with constraints."""

    def __init__(self):
        pass


class BoolTemplate:
    """Template for a boolean with constraints."""

    def __init__(self):
        pass


class ParameterTemplate:
    """Template for a parameter to pass to an operation on an endpoint."""

    def __init__(self, parameter):
        assert parameter.type is not None
        self._type = parameter.type
        assert parameter.name is not None
        self._name = parameter.name

    def __repr__(self):
        return "{}(name={}, type={})".format(self.__class__.__name__,
                                             self._name,
                                             self._type)

    @property
    def name(self):
        return self._name

    @property
    def type(self):
        return self._type


class ModelTemplate:
    """Template for a generic parameter, which may be one of many types,
    defining the model it follows.

    In the Swagger/OpenAPI world, this maps to a `Schema Object`.
    """

    def __init__(self, app, schema):
        self._app = app
        self._schema = schema
        self._contents = None

        self._build()

    @property
    def contents(self):
        return self._contents

    def _build(self):
        # The object may actually be a reference to the definition - if so
        # resolve it.
        ref = getattr(self._schema, '$ref')
        log.debug("Ref is: %r", ref)
        if ref is not None:
            schema = self._app.resolve(ref)
        else:
            schema = self._schema
        log.debug("Schema: %r", schema)
        log.debug("Schema name: %r", schema.name)

        # Populate the model based on its type.
        if schema.type == 'object':
            # If this is an oject with no properties, treat it as a freeform
            # JSON object - which we leave denoted by None.
            log.debug("Properties: %r", schema.properties)
            if len(schema.properties) > 0:
                self._contents = {}
                for prop_name in schema.properties:
                    log.debug("This prop: %r", prop_name)
                    child = ModelTemplate(self._app,
                                          schema.properties[prop_name])
                    self._contents[prop_name] = child
        elif schema.type == 'integer':
            log.debug("Model is integer")
            self._contents = IntegerTemplate()
        elif schema.type == 'string':
            log.debug("Model is string")
            self._contents = StringTemplate()
        elif schema.type == 'number':
            log.debug("Model is float")
            self._contents = FloatTemplate()
        elif schema.type == 'boolean':
            log.debug("Model is boolean")
            self._contents = BoolTemplate()
        else:
            log.warning("SKIPPING SCHEMA TYPE: %r - NOT IMPLEMENTED",
                        schema.type)


class OperationTemplate:
    """Template for an operation on an endpoint."""

    def __init__(self, app, operation):
        self._app = app
        self._operation = operation
        self._parameters = {}
        self._response_codes = [int(code) for code in operation.responses]

        self._populate_parameters()

    def __repr__(self):
        return "{}(operation={}, params={})".format(self.__class__.__name__,
                                                    self._operation,
                                                    self._parameters)

    @property
    def operation(self):
        return self._operation

    @property
    def parameters(self):
        return self._parameters

    @property
    def response_codes(self):
        return self._response_codes

    def _populate_parameters(self):
        for parameter in self._operation.parameters:
            log.debug("Handling parameter: %r", parameter.name)

            # Every parameter has a name. It's either a well defined parameter,
            # or it's the lone body parameter, in which case it's a Model
            # defined by a schema.
            if parameter.name == 'X-Fields':
                log.warning("SKIPPING X-Fields PARAM - NOT IMPLEMENTED")
            elif parameter.schema is None:
                log.debug("Fully defined parameter")
                param_template = ParameterTemplate(parameter)
                self._parameters[parameter.name] = param_template
            else:
                log.debug("Schema defined parameter")
                model_template = ModelTemplate(self._app, parameter.schema)
                self._parameters[parameter.name] = model_template


class APITemplate:

    operations = ["get", "put", "post", "delete"]

    def __init__(self, client):
        log.debug("Creating new endpoint collection for: %r", client)
        self._client = client
        self._app = client.app

        self._paths = self._app.root.paths.keys()
        log.debug("Found paths as: %s", self._paths)

        self._expanded_paths = {}
        for path in self._paths:
            self._expanded_paths[path] = self._expand_path(path)

    @property
    def endpoints(self):
        return self._expanded_paths

    def iter_template_operations(self):
        """All operations of the API across all endpoints.

        :yields: OperationTemplate
        """
        for endpoint in self.endpoints:
            log.debug("Testing endpoint: %r", endpoint)
            for operation_type in self.endpoints[endpoint]:
                log.debug("Testing operation type: %r", operation_type)
                operation = self.endpoints[endpoint][operation_type]
                log.info("Got operation: %r", operation)

                yield operation

    def _expand_path(self, path):
        log.debug("Expanding path: %r", path)

        operations_map = {}
        for operation_name in self.operations:
            log.debug("Accessing operation: %s", operation_name)
            operation = getattr(self._app.root.paths[path], operation_name)
            if operation is not None:
                log.debug("Have operation")
                operations_map[operation_name] = OperationTemplate(self._app,
                                                                   operation)

        log.debug("Expanded path as: %r", operations_map)
        return operations_map
