using System.Collections.Generic;
using SRAFrontend.Models;
using System.Collections.ObjectModel;

namespace SRAFrontend.Migrations;

public static class ConfigMigrator
{
    public static TasksConfig MigrateOldToNew(Config config)
    {
        return new TasksConfig
        {
            Name = config.Name,
            StartGame = new StartGameConfig
            {
                IsEnabled = config.EnabledTasks[0],
                GameChannel = config.StartGameChannel,
                GamePath = config.StartGamePath,
                IsUseGlobalGamePath = config.StartGameUseGlobalPath,
                IsAutoLogin = config.StartGameAutoLogin,
                IsReLogin = config.StartGameAlwaysLogin,
                EncryptedPassword = config.EncryptedStartGamePassword,
                EncryptedUsername = config.EncryptedStartGameUsername,
                Password = config.StartGamePassword,
                Username = config.StartGameUsername
            },
            TrailblazePower = new TrailblazePowerConfig
            {
                IsEnabled = config.EnabledTasks[1],
                IsReplenishEnabled = config.TrailblazePowerReplenishEnable,
                ReplenishTimes = config.TrailblazePowerReplenishTimes,
                ReplenishWay = config.TrailblazePowerReplenishWay,
                IsUseAssistant = config.TrailblazePowerUseAssistant,
                IsUseBuildTarget = config.TrailblazePowerUseBuildTarget,
                TaskList = new ObservableCollection<TrailblazePowerTaskItem>(config.TrailblazePowerTaskList)
            },
            ReceiveRewards = new ReceiveRewardsConfig
            {
                IsEnabled = config.EnabledTasks[2],
                RedeemCodes = config.ReceiveRewardRedeemCodes,
                // 旧配置为按索引对应的布尔列表，可能被人为改短，越界时保留新字段的默认值
                IsTrailblazeProfileEnabled = GetLegacyReward(config.ReceiveRewards, 0, true),
                IsAssignmentsEnabled = GetLegacyReward(config.ReceiveRewards, 1, true),
                IsMailEnabled = GetLegacyReward(config.ReceiveRewards, 2, true),
                IsDailyTrainingEnabled = GetLegacyReward(config.ReceiveRewards, 3, true),
                IsNamelessHonorEnabled = GetLegacyReward(config.ReceiveRewards, 4, true),
                IsGiftOfOdysseyEnabled = GetLegacyReward(config.ReceiveRewards, 5, true),
                IsRedeemCodeEnabled = GetLegacyReward(config.ReceiveRewards, 6, false)
            },
            CosmicStrife = new CosmicStrifeConfig
            {
                IsEnabled = config.EnabledTasks[3],
                IsDivergentUniverseEnabled = config.DUEnable,
                DivergentUniverseMode = config.DUMode,
                DivergentUniverseRuntimes = config.DURunTimes,
                IsDivergentUniverseUseTechnique = config.DUUseTechnique,
                IsCurrencyWarsEnabled = config.CurrencyWarsEnable,
                CurrencyWarsMode = config.CurrencyWarsMode,
                CurrencyWarsRuntimes = config.CurrencyWarsRunTimes,
                CurrencyWarsStrategy = config.CurrencyWarsStrategy,
                CurrencyWarsStrategyIndex = config.CurrencyWarsStrategyIndex,
                CurrencyWarsUsername = config.CurrencyWarsUsername,
                CurrencyWarsDifficulty = config.CurrencyWarsDifficulty,
                CurrencyWarsRerollInvestEnvironments = config.CwRsInvestEnvironments,
                CurrencyWarsRerollInvestStrategies = config.CwRsInvestStrategies,
                CurrencyWarsRerollBossNames = config.CwRsBossNames,
                CurrencyWarsRerollBossAffixes = config.CwRsBossAffixes
            },
            MissionAccomplished = new MissionAccomplishedConfig
            {
                IsEnabled = config.EnabledTasks[4],
                IsExitApp = config.AfterExitApp,
                IsExitGame = config.AfterExitGame,
                IsLogout = config.AfterLogout,
                IsShutdown = config.AfterShutdown,
                IsSleep = config.AfterSleep
            }
        };
    }

    /// <summary>按索引读取旧版奖励开关列表，索引越界（列表被改短）时返回默认值。</summary>
    private static bool GetLegacyReward(IReadOnlyList<bool> rewards, int index, bool defaultValue)
    {
        return index < rewards.Count ? rewards[index] : defaultValue;
    }
}
