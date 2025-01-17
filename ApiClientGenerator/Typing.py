from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Literal

@dataclass
class Contact:
    name: Optional[str]
    url: Optional[str]
    email: Optional[str]

@dataclass
class License:
    name: str
    url: Optional[str]

@dataclass
class Info:
    title: str
    description: Optional[str]
    termsOfService: Optional[str]
    contact: Optional[Contact]
    license: Optional[License]
    version: str

@dataclass
class Tags:
    name: str
    description: Optional[str]

@dataclass
class Response:
    description: str
    content: Optional[Dict[str, Dict[Literal["schema"], Schema]]]

@dataclass
class ServerVariable:
    enum: Optional[List[str]]
    default: str
    description: Optional[str]

@dataclass
class Server:
    url: str
    description: Optional[str]
    variables: Optional[Dict[str, ServerVariable]]

@dataclass
class ExternalDocumentation:
    description: Optional[str]
    url: str

@dataclass
class Tag:
    name: str
    description: Optional[str]
    externalDocs: Optional[ExternalDocumentation]

@dataclass
class Reference:
    ref: str

@dataclass
class Property:
    type: Optional[str]
    format: Optional[str]
    items: Optional[Property]  # Update this line to handle nested properties
    enum: Optional[List[Any]]
    default: Optional[Any]
    nullable: Optional[bool]
    readOnly: Optional[bool]
    writeOnly: Optional[bool]
    description: Optional[str]
    allOf: Optional[List[Property]]
    oneOf: Optional[List[Property]]
    anyOf: Optional[List[Property]]
    not_: Optional[Any]
    properties: Optional[Dict[str, Property]]
    additionalProperties: Optional[Any]
    required: Optional[List[str]]
    example: Optional[Any]
    externalDocs: Optional[ExternalDocumentation]
    deprecated: Optional[bool]
    ref: Optional[str]

@dataclass
class Schema:
    title: Optional[str]
    multipleOf: Optional[float]
    maximum: Optional[float]
    exclusiveMaximum: Optional[bool]
    minimum: Optional[float]
    exclusiveMinimum: Optional[bool]
    maxLength: Optional[int]
    minLength: Optional[int]
    pattern: Optional[str]
    maxItems: Optional[int]
    minItems: Optional[int]
    uniqueItems: Optional[bool]
    maxProperties: Optional[int]
    minProperties: Optional[int]
    required: Optional[List[str]]
    enum: Optional[List[Any]]
    type: Optional[str]
    allOf: Optional[List[Any]]
    oneOf: Optional[List[Any]]
    anyOf: Optional[List[Any]]
    not_: Optional[Any]
    items: Optional[Property]  # Update this line to handle nested properties
    properties: Optional[Dict[str, Property]]
    additionalProperties: Optional[Any]
    description: Optional[str]
    format: Optional[str]
    default: Optional[Any]
    nullable: Optional[bool]
    discriminator: Optional[Dict[str, Any]]
    readOnly: Optional[bool]
    writeOnly: Optional[bool]
    xml: Optional[Dict[str, Any]]
    externalDocs: Optional[ExternalDocumentation]
    example: Optional[Any]
    deprecated: Optional[bool]
    ref: Optional[str]

@dataclass
class Parameter:
    in_: str
    name: str
    schema: Optional[Schema]
    required: Optional[bool]

@dataclass
class Operation:
    summary: Optional[str] = None
    description: Optional[str] = None
    operationId: Optional[str] = None
    parameters: Optional[List[Parameter]] = None
    requestBody: Optional[Dict[str, Any]] = None
    responses: Optional[Dict[str, Response]] = None
    tags: Optional[List[str]] = None

@dataclass
class Path:
    summary: Optional[str] = None
    parameters: Optional[List[Parameter]] = None
    responses: Optional[Dict[str, Response]] = None
    tags: Optional[List[str]] = None

@dataclass
class Components:
    schemas: Optional[Dict[str, Schema]]
    responses: Optional[Dict[str, Response]]
    parameters: Optional[Dict[str, Parameter]]
    examples: Optional[Dict[str, Any]]
    requestBodies: Optional[Dict[str, Any]]
    headers: Optional[Dict[str, Any]]
    securitySchemes: Optional[Dict[str, Any]]
    links: Optional[Dict[str, Any]]
    callbacks: Optional[Dict[str, Any]]

@dataclass
class Methods:
    get: Optional[Path]
    put: Optional[Path]
    post: Optional[Path]
    delete: Optional[Path]
    options: Optional[Path]
    head: Optional[Path]
    patch: Optional[Path]
    trace: Optional[Path]

@dataclass
class OpenAPI:
    openapi: str
    info: Info
    servers: Optional[List[Server]]
    paths: Dict[str, Methods]
    components: Optional[Components]
    security: Optional[List[Dict[str, List[str]]]]
    tags: Optional[List[Tag]]
    externalDocs: Optional[ExternalDocumentation]
