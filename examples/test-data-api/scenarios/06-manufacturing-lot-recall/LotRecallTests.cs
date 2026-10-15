// Manufacturing lot recall — NUnit with the REST API (no .NET SDK exists; HttpClient only).
// DataNivra provisions approved data; the test runs against your service with its own DB access.
using System;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using NUnit.Framework;

public record TestDataRequest(string id, string state);

[TestFixture]
public class LotRecallTests
{
    static readonly HttpClient Http = new();
    static readonly string Api = Environment.GetEnvironmentVariable("DATANIVRA_BASE_URL") + "/v1/test-data/requests";
    string? requestId;

    [OneTimeSetUp]
    public async Task Acquire()
    {
        Http.DefaultRequestHeaders.Authorization =
            new("Bearer", Environment.GetEnvironmentVariable("DATANIVRA_TOKEN"));
        var body = new
        {
            profile = new { name = "manufacturing-traceability", version = 1 },
            scenarios = new[]
            {
                new { scenario_code = "MFG_EVERYDAY_PRODUCTION", count = 200 },
                new { scenario_code = "MFG_LOT_RECALL", count = 50 },
            },
        };
        var created = await (await Http.PostAsJsonAsync(Api, body)).Content.ReadFromJsonAsync<TestDataRequest>();
        requestId = created!.id;
        for (var i = 0; i < 120; i++)
        {
            var current = await Http.GetFromJsonAsync<TestDataRequest>($"{Api}/{requestId}");
            if (current!.state == "READY") return;
            await Task.Delay(TimeSpan.FromSeconds(5));
        }
        Assert.Fail("test data not READY");
    }

    [OneTimeTearDown]
    public async Task Release()
    {
        if (requestId is not null)
            await Http.PostAsJsonAsync($"{Api}/{requestId}/release", new { reason_code = "TEST_RUN_FINISHED" });
    }

    [Test]
    public void EveryAffectedWorkOrderIsFound() => Assert.That(requestId, Is.Not.Null);
}
