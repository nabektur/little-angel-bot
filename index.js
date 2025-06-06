const { AoiClient } = require("aoi.js");
require("dotenv").config(); // .env loading

// Discord Client
const client = new AoiClient({
  token: process.env.DISCORD_TOKEN, 
  prefix: "$",
  intents: ["MessageContent", "Guilds", "GuildMessages"],
  events: ["onMessage", "onInteractionCreate"],
  database: {
      type: "aoi.db",
      db: require("@aoijs/aoi.db"),
      dbType: "KeyValue",
      tables: ["main"],
      securityKey: process.env.SECURITY_KEY
  }
});

client.status({
  name: "на кикстарте",
  type: "STREAMING",
  status: "idle",
  time: 12
});

// Logger
client.readyCommand({
  channel: false,
  code: `console.log("Бот запущен как $userTag[$clientID]")`
});

// Import commands from /commands
client.loadCommands("./commands");