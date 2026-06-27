<div align="center">

# ⚔️ JayBot — Swarajya Bot

### A Maratha Empire themed Discord RPG Bot

*Jay Bhavani! Jay Shivaji!*

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![discord.py](https://img.shields.io/badge/discord.py-2.3+-5865F2?style=for-the-badge&logo=discord)
![SQLite](https://img.shields.io/badge/SQLite-Database-green?style=for-the-badge&logo=sqlite)
![License](https://img.shields.io/badge/License-MIT-orange?style=for-the-badge)

</div>

---

## 🏰 About

**JayBot** is a feature-rich Discord RPG bot inspired by Dragon Ball OV, themed around the **Maratha Empire**. Summon legendary Maratha warriors like Chhatrapati Shivaji Maharaj and Bajirao I, fight Mughal bosses, complete historical story sagas, and climb the Gadkille Tower to prove your worth!

---

## ⚔️ Features

### 🏹 Gacha / Summon System
- Summon warriors from **Swarajya Banner** or **Hindavi Swarajya Banner**
- 4 rarity tiers: 🟡 Legendary · 🟣 Epic · 🔵 Rare · ⚪ Common
- 10x multi-summon with discount
- 16 unique Maratha warriors seeded

### 👤 Profile & Economy
- Player profiles with rank, level, XP bar
- Currency: 🪙 Hon, 💠 Mudra, 🏆 Medals, 💎 Omni Shards
- Daily & hourly Hon rewards
- Leaderboard

### ⚔️ Battle System
- **PvP** — Challenge other players, accept/decline system
- **Boss Battles** — Fight Afzal Khan, Shaista Khan, Aurangzeb & more
- **Boss Key system** — Earn keys from Tower to unlock boss fights
- Element advantage system (Fire > Wind > Earth > Water > Fire)
- Interactive turn-based combat with unique character moves

### 📖 Saga & Mission System
- 6 historical Maratha story sagas
- 4 missions per saga with unique enemies
- Interactive battles — choose moves each turn (1/2/3/4)
- Rewards: Hon, XP, and Boss Keys 🗝️

### 🏰 Gadkille Tower
- 4 difficulty levels: Chaukidar / Havaldar / Sardar / Senapati
- 3-stage interactive battles per difficulty
- 6-hour cooldown
- Hard & Extreme tiers reward Boss Keys

### 🗡️ Characters
- Paginated inventory like DBOV
- Each character has 4 unique named moves
- Info, select, favourite system
- Full warrior gallery

---

## 📜 Commands

### ⚙️ General
| Command | Description |
|---|---|
| `jay!start` | Begin your Swarajya journey |
| `jay!profile` / `jay!pf` | View your Sardar profile |
| `jay!bal` | Check currency balance |
| `jay!daily` | Claim 500 Hon daily reward |
| `jay!roll` | Claim 100 Hon hourly chest |
| `jay!leaderboard` | Top 10 richest players |

### 🏹 Summon
| Command | Description |
|---|---|
| `jay!summon [1/2]` | Single summon (300 Hon) |
| `jay!multi [1/2]` | 10x summon (2700 Hon) |
| `jay!banner` | View available banners |

### ⚔️ Characters
| Command | Description |
|---|---|
| `jay!chars [page]` | Paginated warrior inventory |
| `jay!gallery [page]` | Browse all warriors |
| `jay!info <ID>` | Warrior details & stats |
| `jay!select <ID>` | Equip a warrior |
| `jay!fav <ID>` | Favourite/unfavourite |
| `jay!favs` | View favourites |
| `jay!moves` | Your warrior's moveset |

### ⚔️ Battle
| Command | Description |
|---|---|
| `jay!fight @user` | PvP battle |
| `jay!boss [name]` | Fight a boss (needs 🗝️) |
| `jay!bosses` | View all bosses |
| `jay!stats` | Battle stats |

### 📖 Saga & Missions
| Command | Description |
|---|---|
| `jay!saga` | View all sagas |
| `jay!saga <n>` | Select a saga |
| `jay!mi` | View missions in active saga |
| `jay!mi <n>` | Fight a mission (interactive) |

### 🏰 Tower
| Command | Description |
|---|---|
| `jay!tc` | Tower difficulty menu |
| `jay!tc 1` | Easy — Chaukidar |
| `jay!tc 2` | Medium — Havaldar |
| `jay!tc 3` | Hard — Sardar (rewards 🗝️) |
| `jay!tc 4` | Extreme — Senapati (rewards 2x 🗝️) |
| `jay!keys` | Check Boss Keys |

---

## 🏛️ Maratha Warriors

| Rarity | Warriors |
|---|---|
| 🟡 Legendary | Chhatrapati Shivaji Maharaj, Bajirao I, Chhatrapati Sambhaji Maharaj, Tarabai |
| 🟣 Epic | Tanaji Malusare, Murarbaji Deshpande, Netaji Palkar, Hambirrao Mohite |
| 🔵 Rare | Mavla Soldier, Sardar Horseman, Peshwa Guard, Konkan Scout |
| ⚪ Common | Foot Soldier, Village Warrior, River Guard, Hill Ranger |

---

## 👹 Bosses (Enemies of Swarajya)

| Boss | Title | Difficulty |
|---|---|---|
| Siddi Jauhar | Adilshahi Admiral | ⭐⭐ |
| Afzal Khan | Adilshahi General | ⭐⭐⭐ |
| Jai Singh I | Rajput-Mughal General | ⭐⭐⭐ |
| Shaista Khan | Mughal Viceroy | ⭐⭐⭐⭐ |
| Aurangzeb | Mughal Emperor | ⭐⭐⭐⭐⭐ |

---

## 🚀 Setup

### Prerequisites
- Python 3.10+
- A Discord Bot Token ([discord.com/developers](https://discord.com/developers/applications))

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/sarthakshinde8022/JayBot.git
cd JayBot

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file
echo "DISCORD_TOKEN=your_token_here" > .env

# 4. Run the bot
python main.py
```

### Bot Permissions Required
- Send Messages
- Read Messages / View Channels
- Embed Links
- Read Message History

### Required Discord Intent
Enable **Message Content Intent** in the Discord Developer Portal → Bot tab.

---

## 🗂️ Project Structure

```
JayBot/
├── main.py          # Bot entry point, help command
├── database.py      # SQLite setup, all seeds
├── config.py        # Rarities, rates, economy constants
├── requirements.txt
└── cogs/
    ├── general.py   # start, profile, bal, daily, roll, leaderboard
    ├── characters.py # summon, chars, gallery, info, select, fav
    ├── battle.py    # fight, boss, stats, moves
    ├── saga.py      # saga, mission (interactive)
    └── tower.py     # tower challenge, boss keys
```

---

## 🗺️ Roadmap

- [x] Phase 1 — Profile, Economy, Gacha
- [x] Phase 2 — PvP, Boss Battles
- [x] Phase 3a — Sagas, Missions, Tower, Boss Keys
- [ ] Phase 3b — Items & Equipment, War Animals (Pets)
- [ ] Phase 4 — Clans, Market, Trading
- [ ] Phase 5 — Fusion, Awakening, Soul Boost

---

## 🙏 Credits

- Inspired by **Dragon Ball OV** Discord bot
- Themed around the **Maratha Empire** history
- Built with [discord.py](https://discordpy.readthedocs.io/)

---

<div align="center">

*Jay Bhavani! Jay Shivaji! 🚩*

</div>
