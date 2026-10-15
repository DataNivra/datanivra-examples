"""Performance volume with a hard ceiling: a Locust load script.

Acquire the data first with the CLI, then run Locust against *your application* (not DataNivra):

    ID=$(datanivra test-data request request.yaml --wait -o json | jq -r .id)
    locust -f locustfile.py --headless -u 20 -r 5 -t 5m --host https://app.example.test
    datanivra test-data release "$ID" --reason-code LOAD_TEST_FINISHED

DataNivra provisions the volume; Locust generates the load. All data is synthetic.
"""

from locust import HttpUser, between, task


class OrdersReader(HttpUser):
    """Reads pages of the provisioned synthetic orders; a slow page counts as a failure."""

    wait_time = between(0.1, 0.5)

    @task
    def list_orders(self) -> None:
        with self.client.get("/orders?limit=100", catch_response=True) as res:
            if res.status_code != 200:
                res.failure(f"status {res.status_code}")
            elif res.elapsed.total_seconds() > 0.5:
                res.failure("slower than 500 ms")
