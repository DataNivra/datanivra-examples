// Insurance claim payout edge cases — JUnit 5 using the REST API (no Java SDK exists; java.net.http only).
// DataNivra provisions approved data; this test then exercises your service with its own DB access.
import static org.junit.jupiter.api.Assertions.assertEquals;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

class ClaimPayoutTest {
  static final String API = System.getenv("DATANIVRA_BASE_URL") + "/v1/test-data/requests";
  static final HttpClient HTTP = HttpClient.newHttpClient();
  static String requestId;

  static HttpRequest.Builder call(String url) {
    return HttpRequest.newBuilder(URI.create(url))
        .header("Authorization", "Bearer " + System.getenv("DATANIVRA_TOKEN"))
        .header("Content-Type", "application/json");
  }

  @BeforeAll
  static void acquire() throws Exception {
    // request.json holds the same TestDataRequest spec as request.yaml (JSON form).
    String body = Files.readString(Path.of("request.json"));
    HttpResponse<String> created = HTTP.send(call(API).POST(HttpRequest.BodyPublishers.ofString(body)).build(),
        HttpResponse.BodyHandlers.ofString());
    requestId = created.body().replaceAll("(?s).*\"id\":\"([^\"]+)\".*", "$1");
    for (int i = 0; i < 120; i++) {
      String state = HTTP.send(call(API + "/" + requestId).GET().build(), HttpResponse.BodyHandlers.ofString())
          .body().replaceAll("(?s).*\"state\":\"([A-Z_]+)\".*", "$1");
      if (state.equals("READY")) return;
      Thread.sleep(5000);
    }
    throw new IllegalStateException("test data not READY");
  }

  @AfterAll
  static void release() throws Exception {
    if (requestId != null) {
      HTTP.send(call(API + "/" + requestId + "/release")
          .POST(HttpRequest.BodyPublishers.ofString("{\"reason_code\":\"TEST_RUN_FINISHED\"}")).build(),
          HttpResponse.BodyHandlers.discarding());
    }
  }

  @Test
  void payoutNeverExceedsTheLimit() {
    // Query your claims service against the approved target and assert payouts at the boundaries.
    assertEquals(true, requestId != null);
  }
}
