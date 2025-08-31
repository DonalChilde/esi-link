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


## Sub packages and theit areas of responsiblity

Where possible descrete bit of behavior will be broken up into sub packages, to make the problem space a bit smaller, and allow a more modular project layout.

### CLI

The esl-link cli will be built with typer. The commands will be logically grouped in files, based on behavior and area of responsibility. For example, the command to output the possible ESI operations might look like `esi-link schema operations --simple-list`. the esi-link entry point will be in its own file, the schema sub command will be in its own file with any related behavior, and the operations command will be in its own file.

In the future, more elaborate interfaces will be considered in order to lean into the `cli-first` aspect of esi-link. For instance a user interface based on [textual](https://textual.textualize.io/).

### schema_store

The schema_store module handles loading and saving a copy of the ESI api schema to file, and also downloading it from the internet. The compatability_date for the ESI api is derived from the download date of the schema. Currently only one copy of the schema is stored, but in the future schema_store should support multiple different copies of the schema so that users can be offered consistent ESI api behavior even after a schema updated.

### schema_types

schema_types offers a partial representation of the openapi 3.1 schema as TypedDicts. This is thought to be useful solely for typechecking, but may be used in concrete form later. Not ready for use.

### eve_openapi

The eve_openapi module offers an api - defined in the eve_openapi_protocol -  for working with the contents of the ESI schema. The current implementation needs to be expanded, to offer access to more parts of the esi operations. Header, path_parameter, query_parameters, along with the success output schema should be able to be requested by operation id. Any internal references should dereferenced and returned along with the operation specific data. 

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