*** Settings ***
Documentation     Cross-account authorization with approved synthetic data (REST; RequestsLibrary).
...               DataNivra provisions the data; this suite tests your API's access control.
Library           RequestsLibrary
Library           OperatingSystem
Suite Setup       Acquire Test Data
Suite Teardown    Release Test Data

*** Variables ***
${API}            %{DATANIVRA_BASE_URL}/v1/test-data/requests

*** Keywords ***
Acquire Test Data
    ${headers}=    Create Dictionary    Authorization=Bearer %{DATANIVRA_TOKEN}
    Create Session    dn    %{DATANIVRA_BASE_URL}    headers=${headers}
    ${body}=    Get File    request.json
    ${created}=    POST On Session    dn    /v1/test-data/requests    data=${body}    expected_status=201
    Set Suite Variable    ${REQUEST_ID}    ${created.json()}[id]
    Wait Until Keyword Succeeds    10 min    5 s    Request Is Ready

Request Is Ready
    ${current}=    GET On Session    dn    /v1/test-data/requests/${REQUEST_ID}
    Should Be Equal    ${current.json()}[state]    READY

Release Test Data
    POST On Session    dn    /v1/test-data/requests/${REQUEST_ID}/release    json=${{ {"reason_code": "TEST_RUN_FINISHED"} }}

*** Test Cases ***
Other Owner's Account Is Not Visible
    # Call your API as owner A with an account id of owner B and expect 403 or 404.
    Log    Test data request ${REQUEST_ID} is READY
