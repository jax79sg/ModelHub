# Logical Components: artifactory-stand-in

The stand-in is one process started inside a test run. Its parts are logical, not separate programs.

| Component | Role | Failure domain | Blast radius if it fails |
|-----------|------|----------------|--------------------------|
| Call handler | Receives the imitated Hugging Face and Artifactory calls | The stand-in process | Only the test that started it |
| Rule engine | Applies the rules BR1.1 to BR1.16 in order | The stand-in process | Only the test |
| Version store | Holds repositories, versions and files | The stand-in process | Only the test; state vanishes when it stops |
| Content area | Temporary folder for kept files | Local disk of the build machine | Only the test |
| Failure switch table | Holds instructions to misbehave | The stand-in process | Only the test |
| Call record | Holds the calls received | The stand-in process | Only the test |
| Assumption register | Data file read by tests | Source tree | None at run time |
