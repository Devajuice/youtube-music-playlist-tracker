# 🎵 YouTube Music Playlist Monitor Bot

A Telegram bot that monitors your YouTube Music playlist and sends real-time notifications when songs are added or removed, complete with album artwork!

## ✨ Features

- 🔔 **Real-time Notifications** - Get instant updates when songs are added or removed
- 🎨 **Album Artwork** - Beautiful notifications with square album covers
- 🔗 **Direct Links** - Click to listen on YouTube Music instantly
- 🤖 **24/7 Monitoring** - Runs continuously on Render with UptimeRobot
- 👥 **Multi-user Support** - Multiple users can subscribe to the same bot

## 📋 Commands

- `/start` - Subscribe to playlist notifications
- `/stop` - Unsubscribe from notifications
- `/status` - Check bot status and subscription info
- `/check` - Manually check for playlist updates
- `/help` - Show detailed help information

## 🚀 Deployment Guide

### Prerequisites

1. **Telegram Bot Token**
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Send `/newbot` and follow instructions
   - Copy your bot token

2. **YouTube Music Playlist ID**
   - Open your playlist in YouTube Music
   - Copy the playlist ID from the URL (after `list=`)
   - Example: `PLxxxxxxxxxxxxxxxxxxxxxx`

### Deploy to Render

1. **Fork this repository** to your GitHub account

2. **Sign up** at [Render.com](https://render.com)

3. **Create a New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure:
     - **Name**: `youtube-music-bot` (or your choice)
     - **Environment**: `Python 3`
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `python bot.py`
     - **Instance Type**: Free

4. **Add Environment Variables** (in Render dashboard):

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
YOUTUBE_PLAYLIST_ID=your_playlist_id_here
CHECK_INTERVAL=300
```

5. **Deploy** - Click "Create Web Service"

### Setup UptimeRobot (Keep Bot Alive 24/7)

1. **Sign up** at [UptimeRobot.com](https://uptimerobot.com)

2. **Create Monitor**:

- Click "Add New Monitor"
- Monitor Type: `HTTP(s)`
- Friendly Name: `YouTube Music Bot`
- URL: `https://your-app-name.onrender.com` (from Render)
- Monitoring Interval: `5 minutes`

3. **Save** - Your bot will now stay alive 24/7!

## 🛠️ Local Development

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/youtube-music-telegram-bot.git
cd youtube-music-telegram-bot
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment variables**

```bash
cp .env.example .env
```

5. **Run the bot**

```bash
python bot.py
```

## 📁 Project Structure

```
youtube-music-telegram-bot/
├── bot.py # Main bot logic
├── keep_alive.py # Flask server for UptimeRobot
├── requirements.txt # Python dependencies
├── runtime.txt # Python version
├── .env.example # Environment variables template
├── .gitignore # Git ignore rules
└── README.md # This file
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token from BotFather | Required |
| `YOUTUBE_PLAYLIST_ID` | YouTube Music playlist ID to monitor | Required |
| `CHECK_INTERVAL` | Check interval in seconds | 300 (5 minutes) |

## 📸 Screenshots

[Add screenshots of your bot notifications here]

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Troubleshooting

### Bot not detecting changes

- Delete `playlist_state.json` and run `/check` to reinitialize
- Verify your playlist ID is correct

### Authentication errors

- Make sure your playlist is public or properly authenticated
- Check your bot token is correct

### Bot goes offline on Render free tier

- Ensure UptimeRobot is configured correctly
- Render free tier sleeps after 15 minutes of inactivity

## 💡 Tips

- The bot checks every 5 minutes by default (configurable)
- Use `/check` to force an immediate update
- Multiple users can subscribe to the same bot
- Album artwork is automatically fetched from YouTube Music

## 📧 Support

If you encounter any issues or have questions:

- Open an issue on GitHub
- Check existing issues for solutions

## 🌟 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
- [ytmusicapi](https://github.com/sigma67/ytmusicapi) - YouTube Music API
- [Render](https://render.com) - Hosting platform
- [UptimeRobot](https://uptimerobot.com) - Uptime monitoring

---

Made with ❤️ by [Devajuice]
