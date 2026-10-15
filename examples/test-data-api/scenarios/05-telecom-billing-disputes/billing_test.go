// Telecom billing disputes — Go testing with the REST API (no Go SDK exists).
// DataNivra provisions approved data; your tests use the approved target with their own credentials.
package billing

import (
	"bytes"
	"encoding/json"
	"net/http"
	"os"
	"testing"
	"time"
)

type testDataRequest struct {
	ID    string `json:"id"`
	State string `json:"state"`
}

func call(method, url string, body []byte) (*http.Response, error) {
	req, err := http.NewRequest(method, url, bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+os.Getenv("DATANIVRA_TOKEN"))
	req.Header.Set("Content-Type", "application/json")
	return http.DefaultClient.Do(req)
}

func TestDisputedBillsAreAdjusted(t *testing.T) {
	api := os.Getenv("DATANIVRA_BASE_URL") + "/v1/test-data/requests"
	body := []byte(`{"profile":{"name":"telecom-billing","version":1},` +
		`"scenarios":[{"scenario_code":"TEL_EVERYDAY_USAGE","count":300},{"scenario_code":"TEL_DISPUTED_BILLS","count":100}]}`)
	resp, err := call(http.MethodPost, api, body)
	if err != nil || resp.StatusCode != http.StatusCreated {
		t.Fatalf("request failed: %v", err)
	}
	var created testDataRequest
	_ = json.NewDecoder(resp.Body).Decode(&created)
	defer call(http.MethodPost, api+"/"+created.ID+"/release", []byte(`{"reason_code":"TEST_RUN_FINISHED"}`))
	for i := 0; i < 120 && created.State != "READY"; i++ {
		time.Sleep(5 * time.Second)
		r, _ := call(http.MethodGet, api+"/"+created.ID, nil)
		_ = json.NewDecoder(r.Body).Decode(&created)
	}
	if created.State != "READY" {
		t.Fatalf("test data not ready: %s", created.State)
	}
	// Exercise your billing service against the approved target here.
}
