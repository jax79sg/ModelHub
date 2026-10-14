# Performance Design: portal

How the portal meets its page targets: it adds little on top of the Catalog.

| Requirements | Design decision | How it works |
|--------------|-----------------|--------------|
| NFR2.1, NFR7.1 | Thin server-side pages over one Catalog call each | A list page makes one Catalog call and renders a template; the Catalog does the filtering; no cache; 20 people at once fit in a single worker pool of 4 workers. |
| NFR2.2 | Model page from two calls | The model page uses the model call and the version call; the README is rendered by the existing sanitiser once per request; pictures are separate cacheable requests. |
| NFR2.3 | Light pages, no outside files | Styles and scripts are served by the portal with long cache lifetimes and a version in the file name; script is optional; pictures are loaded lazily. |
| NFR2.4 | Sign-in steps do little work | The redirect and the callback do one request each to Keycloak and store the session. |
| NFR1.1 | No portal cache | Every page reads the Catalog, so a new model appears at once. |
