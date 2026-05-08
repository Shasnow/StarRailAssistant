using System;
using System.IO;
using System.Text.Json;
using Microsoft.Extensions.Logging;
using SRAFrontend.Data;
using SRAFrontend.Models;

namespace SRAFrontend.Services;

public class CosmicStrifePolicyStateService(ILogger<CosmicStrifePolicyStateService> logger)
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true
    };

    public CosmicStrifePolicyState State { get; private set; } = new();

    public string StatePath => Path.Combine(PathString.AppDataDir, "cosmic_strife_policy_state.json");

    public void Refresh()
    {
        try
        {
            if (!File.Exists(StatePath))
            {
                State = new CosmicStrifePolicyState();
                return;
            }

            var json = File.ReadAllText(StatePath);
            if (string.IsNullOrWhiteSpace(json))
            {
                State = new CosmicStrifePolicyState();
                return;
            }

            State = JsonSerializer.Deserialize<CosmicStrifePolicyState>(json, JsonOptions) ?? new CosmicStrifePolicyState();
        }
        catch (Exception e)
        {
            logger.LogWarning(e, "Failed to load cosmic strife policy state, using empty state.");
            State = new CosmicStrifePolicyState();
        }
    }
}

