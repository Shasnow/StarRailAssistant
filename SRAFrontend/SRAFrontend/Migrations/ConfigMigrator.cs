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
                Rewards = new ObservableCollection<bool>(config.ReceiveRewards)
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
}
