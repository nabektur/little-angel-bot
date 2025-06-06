const { AoiClient } = require("aoi.js");
require("dotenv").config(); // .env loading

// Discord Client
const client = new AoiClient({
  token: process.env.DISCORD_TOKEN, 
  prefix: "$",
  intents: ["MessageContent", "Guilds", "GuildMessages"],
  events: ["onMessage", "onInteractionCreate"]
});

client.status({
  name: "Я Оставил ДРУЗЕЙ в Заброшенном Городе!",
  type: "STREAMING",
  url: "https://www.youtube.com/@%D0%BC%D0%B8%D1%81%D1%82%D0%B5%D1%80-%D0%B4%D1%8D%D0%BF",
  status: "idle",
  time: 12
});

// Logger
client.readyCommand({
  channel: "1380518098053894146",
  code: `"Бот запущен как **$userTag[$clientID]**`
});

// Import commands from /commands
client.loadCommands("./commands");