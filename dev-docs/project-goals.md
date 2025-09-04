# Project Goals

Project Name - esi-link
Started On - 2025-08-31
Inline Documentation style - [Google](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)

Esi-Link is meant to be a front end to the Eve Online ESI API. It will be command line first, with the ability to make an esi request in the terminal. Data received will be the response headers and the raw strings, with ouptions for output in a number of formats. For instance, json of just the received data, json of the data with headers, json of the data and headers with an id passed in with the initial query, csv, or just plain text.

Batch requests will be possible, with the queries loaded from a json file.

Paged queries will be batched internally to take advantage of concurrent requests.

Get requests will be cached, to avoid hitting the server before fresh data is available.

An API will allow programatic access to esi-link functionality.

At the moment, authenticated requests are not officially supported, though it should be possible by manually passing in the tokens with the query headers.

The esi-link will manage downloading and storing the ESI openapi schema.

The esi-link cli will be able to list all the available operations, along with descriptions, parameter requirements, and return data format.

In the future, esi-link will offer some internally integrated dataset downloads, in particular a download of the "static" data as a package, with some tables merged for better use. Some examples of this would be region ids and names in one json. Aggregated system information. Type information with collected group, category, and market group information suitable for export in csv format.

## Sub packages and their areas of responsiblity

Where possible descrete bit of behavior will be broken up into sub packages, to make the problem space a bit smaller, and allow a more modular project layout.

### CLI

The esl-link cli will be built with typer. The commands will be logically grouped in files, based on behavior and area of responsibility. For example, the command to output the possible ESI operations might look like `esi-link schema operations --simple-list`. the esi-link entry point will be in its own file, the schema sub command will be in its own file with any related behavior, and the operations command will be in its own file.

In the future, more elaborate interfaces will be considered in order to lean into the `cli-first` aspect of esi-link. For instance a user interface based on [textual](https://textual.textualize.io/).

### schema_store

The schema_store module handles loading and saving a copy of the ESI api schema to file, and also downloading it from the internet. The compatability_date for the ESI api is derived from the download date of the schema. Currently only one copy of the schema is stored, but in the future schema_store should support multiple different copies of the schema so that users can be offered consistent ESI api behavior even after a schema updated.

### schema_types

schema_types offers a partial representation of the openapi 3.1 schema as TypedDicts. This is thought to be useful solely for typechecking, but may be used in concrete form later. Not ready for use.

### eve_openapi

The eve_openapi module offers an api - defined in the eve_openapi_protocol - for working with the contents of the ESI schema. The current implementation needs to be expanded, to offer access to more parts of the esi operations. Header, path_parameter, query_parameters, along with the success output schema should be able to be requested by operation id. Any internal references should dereferenced and returned along with the operation specific data.

### link_cache

The link_cache modules provide an api to cache certain ESI api requests. link_cache_protocol ddefines the api, and there are currently a memory only, and a hybrid memory/filebased cache that allows cache continuity between cli invocations. In the future, a sqlite based cache will be considered.

### esi_client

esi_client is the entry point for making an esi query. This level of code might be the right place for the top level user facing object, that contains the schema, cache, and confguration for queries.

### esi_link.esi_link

esi_link (name to be refactored, as two esi_links is confusing) has the api for network calls, and managing async tasks.

## Next steps

- Make tests for all existing code to confirm function and behavior.
- Update documentation for existing code.
- Make cli commands to test request and retrieval of simple queries, with plain text and `QueryResponse` json format.
- Implement retrieval and display of operation information, and make that available through the cli.
- Implement the first version of batched requests from the cli.
- Implement more output options.
- Test non-get un-authenticed queries to see if the EsiQuery object needs to be updated. Most of the queries we need first are un-authenticated get requests, its ok to wait to work on other methods.

### Validating queries

Validate queries to catch missing/extra parameters before sending query.

#### TODO

- [] clean up request validation code. Split function outside the class to make refactors and testinf easier.

### Query docs from cli

- Show lists of operations and descriptions from the cli
- Show detailed information on query request parameters, and return values.

#### TODO

- [] implement limited docs for operations, Query Request is easy, response doc is more complicated. just do request for now.

## Schema Doc/Def

- The schema for `arrays` of parameters in `["requestBody","response",["200","201]]` look like this:

```json
{
  "schema": {
    "items": {
      "description": "item_id integer",
      "format": "int64",
      "type": "integer"
    },
    "maxItems": 1000,
    "minItems": 1,
    "type": "array",
    "uniqueItems": true
  }
}
```

- The schema for `objects` of parameters in `["requestBody","response",["200","201]]` look like this:

```json
{
  "schema": {
    "properties": {
      "is_free_move": {
        "description": "Should free-move be enabled in the fleet",
        "type": "boolean"
      },
      "motd": {
        "description": "New fleet MOTD in CCP flavoured HTML",
        "type": "string"
      }
    },
    "type": "object"
  }
}
```

- The schema for ["number"] in `["requestBody","response",["200","201]]` looks like:

```json
{
  "schema": {
    "description": "201 created number",
    "format": "double",
    "type": "number"
  }
}
```

- The a `204` response schema looks like this:

```json
{
  "204": {
    "description": "Label deleted",
    "headers": {
      "Cache-Control": {
        "description": "Directives for caching mechanisms. It controls how the response can be cached, by whom, and for how long.",
        "schema": {
          "type": "string"
        }
      },
      "ETag": {
        "description": "The ETag value of the response body. Use this with If-None-Match to check whether the resource has changed.",
        "schema": {
          "type": "string"
        }
      },
      "Last-Modified": {
        "description": "The last modified date of the response. Use this with If-Modified-Since to check whether the resource has changed.",
        "schema": {
          "type": "string"
        }
      }
    }
  }
}
```

- The `201` response schema looks like:

```json
{
  "201": {
    "content": {
      "application/json": {
        "schema": {
          "description": "201 created object",
          "properties": {
            "wing_id": {
              "description": "The wing_id of the newly created wing",
              "format": "int64",
              "type": "integer"
            }
          },
          "required": ["wing_id"],
          "type": "object"
        }
      }
    },
    "description": "Created",
    "headers": {
      "Cache-Control": {
        "description": "Directives for caching mechanisms. It controls how the response can be cached, by whom, and for how long.",
        "schema": {
          "type": "string"
        }
      },
      "ETag": {
        "description": "The ETag value of the response body. Use this with If-None-Match to check whether the resource has changed.",
        "schema": {
          "type": "string"
        }
      },
      "Last-Modified": {
        "description": "The last modified date of the response. Use this with If-Modified-Since to check whether the resource has changed.",
        "schema": {
          "type": "string"
        }
      }
    }
  }
}
```

- The `200` response schema looks like:

```json
{
  "200": {
    "content": {
      "application/json": {
        "schema": {
          "items": {
            "properties": {
              "contested": {
                "enum": ["captured", "contested", "uncontested", "vulnerable"],
                "type": "string"
              },
              "occupier_faction_id": {
                "format": "int64",
                "type": "integer"
              },
              "owner_faction_id": {
                "format": "int64",
                "type": "integer"
              },
              "solar_system_id": {
                "format": "int64",
                "type": "integer"
              },
              "victory_points": {
                "format": "int64",
                "type": "integer"
              },
              "victory_points_threshold": {
                "format": "int64",
                "type": "integer"
              }
            },
            "required": [
              "solar_system_id",
              "occupier_faction_id",
              "owner_faction_id",
              "victory_points",
              "victory_points_threshold",
              "contested"
            ],
            "type": "object"
          },
          "type": "array"
        }
      }
    },
    "description": "OK",
    "headers": {
      "Cache-Control": {
        "description": "Directives for caching mechanisms. It controls how the response can be cached, by whom, and for how long.",
        "schema": {
          "type": "string"
        }
      },
      "ETag": {
        "description": "The ETag value of the response body. Use this with If-None-Match to check whether the resource has changed.",
        "schema": {
          "type": "string"
        }
      },
      "Last-Modified": {
        "description": "The last modified date of the response. Use this with If-Modified-Since to check whether the resource has changed.",
        "schema": {
          "type": "string"
        }
      }
    }
  }
}
```

- The request parameters look like:

```json
{
  "parameters": [
    {
      "description": "The ID of the character",
      "in": "path",
      "name": "character_id",
      "required": true,
      "schema": {
        "examples": [90000001],
        "format": "int64",
        "type": "integer",
        "x-common-model": "true"
      }
    },
    {
      "description": "The language to use for the response.",
      "in": "header",
      "name": "Accept-Language",
      "schema": {
        "default": "en",
        "enum": ["en", "de", "fr", "ja", "ru", "zh", "ko", "es"],
        "type": "string"
      }
    },
    {
      "description": "The ETag of the previous request. A 304 will be returned if this matches the current ETag.",
      "in": "header",
      "name": "If-None-Match",
      "schema": {
        "type": "string"
      }
    },
    {
      "description": "The compatibility date for the request.",
      "in": "header",
      "name": "X-Compatibility-Date",
      "required": true,
      "schema": {
        "enum": ["2020-01-01"],
        "format": "date",
        "type": "string"
      }
    },
    {
      "description": "The tenant ID for the request.",
      "example": "",
      "in": "header",
      "name": "X-Tenant",
      "schema": {
        "default": "tranquility",
        "type": "string"
      }
    }
  ]
}
```

- Operation query parameters are a list of dicts, scoped to `["path","header","query"]` by the "in" key.
- `get` operations return `["Responses"]["200"]`
- `["put","post"]` operations return `["Responses"]["204"]` for "No Content" responses and `["Responses"]["201"]` for responses with data.
- `["put","post"]` operations also have the `"requestBody"` key, which contains `["object',"array"]` of parameters
