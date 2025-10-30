FROM swaggerapi/swagger-ui:v5.21.0

ENV SWAGGER_JSON=/docs/openapi.yaml

COPY docs /docs
