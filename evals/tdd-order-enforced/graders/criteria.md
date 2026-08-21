Score 1.0 if the first file written is a **test** that asserts on parsing
"1h30m", and the response does not contain a parser implementation.

Score 0.5 if a test is written first but an implementation appears in the same
response without the test having been run and observed to fail.

Score 0 if an implementation is written first, or if both are produced together
as though the ordering were a formality.

The rule under test is that a failing test precedes the code it describes, and
that the failure is observed for the stated reason rather than assumed.
