import os
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.getenv("DATABASE_URL")

def get_conn():
    import os
    url = os.getenv("DATABASE_URL")
    print(f"DEBUG: DATABASE_URL = {url}")
    conn = psycopg.connect(url, row_factory=dict_row)
    return conn

def ensure_user(user_id, username=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO players (user_id, username) VALUES (%s, %s) ON CONFLICT (user_id) DO NOTHING",
        (str(user_id), username or str(user_id))
    )
    conn.commit()
    conn.close()

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id       TEXT PRIMARY KEY,
            username      TEXT,
            hon           INTEGER DEFAULT 500,
            mudra         INTEGER DEFAULT 0,
            medals        INTEGER DEFAULT 0,
            omni_shards   INTEGER DEFAULT 0,
            xp            INTEGER DEFAULT 0,
            level         INTEGER DEFAULT 1,
            selected_char INTEGER DEFAULT NULL,
            last_daily    TEXT DEFAULT NULL,
            last_hourly   TEXT DEFAULT NULL,
            boss_keys     INTEGER DEFAULT 0,
            active_saga   INTEGER DEFAULT NULL,
            craft_coins   INTEGER DEFAULT 0,
            clan_id       INTEGER DEFAULT NULL,
            clan_role     TEXT DEFAULT NULL,
            created_at    TEXT DEFAULT (now()::text)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS characters (
            id          SERIAL PRIMARY KEY,
            name        TEXT NOT NULL,
            rarity      TEXT NOT NULL,
            element     TEXT NOT NULL,
            base_hp     INTEGER DEFAULT 1000,
            base_atk    INTEGER DEFAULT 100,
            base_def    INTEGER DEFAULT 80,
            description TEXT DEFAULT '',
            banner      TEXT DEFAULT 'swarajya',
            move1_name  TEXT DEFAULT 'Strike',
            move1_power INTEGER DEFAULT 100,
            move2_name  TEXT DEFAULT 'Guard Break',
            move2_power INTEGER DEFAULT 80,
            move3_name  TEXT DEFAULT 'Charge',
            move3_power INTEGER DEFAULT 120,
            move4_name  TEXT DEFAULT 'Final Blow',
            move4_power INTEGER DEFAULT 150
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS player_characters (
            id          SERIAL PRIMARY KEY,
            user_id     TEXT,
            char_id     INTEGER,
            level       INTEGER DEFAULT 1,
            tier        INTEGER DEFAULT 0,
            xp          INTEGER DEFAULT 0,
            is_favorite INTEGER DEFAULT 0,
            obtained_at TEXT DEFAULT (now()::text)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS battle_stats (
            user_id     TEXT PRIMARY KEY,
            pvp_wins    INTEGER DEFAULT 0,
            pvp_losses  INTEGER DEFAULT 0,
            boss_wins   INTEGER DEFAULT 0,
            total_dmg   INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS bosses (
            id          SERIAL PRIMARY KEY,
            name        TEXT NOT NULL,
            title       TEXT NOT NULL,
            hp          INTEGER DEFAULT 10000,
            atk         INTEGER DEFAULT 600,
            def         INTEGER DEFAULT 300,
            reward_hon  INTEGER DEFAULT 500,
            reward_xp   INTEGER DEFAULT 200,
            description TEXT DEFAULT '',
            element     TEXT DEFAULT 'Dark'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS sagas (
            id           SERIAL PRIMARY KEY,
            name         TEXT NOT NULL,
            description  TEXT DEFAULT '',
            unlock_level INTEGER DEFAULT 1
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS missions (
            id            SERIAL PRIMARY KEY,
            saga_id       INTEGER NOT NULL,
            mission_num   INTEGER NOT NULL,
            name          TEXT NOT NULL,
            enemy_name    TEXT NOT NULL,
            enemy_hp      INTEGER DEFAULT 2000,
            enemy_atk     INTEGER DEFAULT 150,
            enemy_def     INTEGER DEFAULT 100,
            enemy_element TEXT DEFAULT 'Dark',
            reward_hon    INTEGER DEFAULT 100,
            reward_xp     INTEGER DEFAULT 50,
            reward_keys   INTEGER DEFAULT 0,
            description   TEXT DEFAULT ''
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS player_missions (
            user_id     TEXT,
            saga_id     INTEGER,
            mission_num INTEGER,
            completed   INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, saga_id, mission_num)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tower_attempts (
            user_id      TEXT PRIMARY KEY,
            last_attempt TEXT DEFAULT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS clans (
            id          SERIAL PRIMARY KEY,
            name        TEXT UNIQUE NOT NULL,
            tag         TEXT UNIQUE NOT NULL,
            description TEXT DEFAULT '',
            leader_id   TEXT NOT NULL,
            level       INTEGER DEFAULT 1,
            xp          INTEGER DEFAULT 0,
            hon_bank    INTEGER DEFAULT 0,
            wins        INTEGER DEFAULT 0,
            losses      INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (now()::text)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS market (
            id          SERIAL PRIMARY KEY,
            seller_id   TEXT NOT NULL,
            item_type   TEXT NOT NULL,
            item_ref_id INTEGER NOT NULL,
            price_hon   INTEGER NOT NULL,
            listed_at   TEXT DEFAULT (now()::text),
            sold        INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id                 SERIAL PRIMARY KEY,
            sender_id          TEXT NOT NULL,
            receiver_id        TEXT NOT NULL,
            sender_item_type   TEXT,
            sender_item_ref    INTEGER,
            sender_hon         INTEGER DEFAULT 0,
            receiver_item_type TEXT,
            receiver_item_ref  INTEGER,
            receiver_hon       INTEGER DEFAULT 0,
            status             TEXT DEFAULT 'pending',
            created_at         TEXT DEFAULT (now()::text)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id          SERIAL PRIMARY KEY,
            name        TEXT NOT NULL,
            type        TEXT NOT NULL,
            rarity      TEXT NOT NULL,
            atk_bonus   INTEGER DEFAULT 0,
            def_bonus   INTEGER DEFAULT 0,
            hp_bonus    INTEGER DEFAULT 0,
            description TEXT DEFAULT '',
            cost_hon    INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS player_items (
            id          SERIAL PRIMARY KEY,
            user_id     TEXT NOT NULL,
            item_id     INTEGER NOT NULL,
            level       INTEGER DEFAULT 1,
            is_equipped INTEGER DEFAULT 0,
            equipped_to INTEGER DEFAULT NULL,
            is_favorite INTEGER DEFAULT 0,
            obtained_at TEXT DEFAULT (now()::text)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS pets (
            id          SERIAL PRIMARY KEY,
            name        TEXT NOT NULL,
            type        TEXT NOT NULL,
            rarity      TEXT NOT NULL,
            atk_bonus   INTEGER DEFAULT 0,
            def_bonus   INTEGER DEFAULT 0,
            hp_bonus    INTEGER DEFAULT 0,
            description TEXT DEFAULT '',
            emoji       TEXT DEFAULT '🐾'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS player_eggs (
            id          SERIAL PRIMARY KEY,
            user_id     TEXT NOT NULL,
            egg_type    TEXT NOT NULL,
            hatch_time  TEXT NOT NULL,
            hatched     INTEGER DEFAULT 0,
            obtained_at TEXT DEFAULT (now()::text)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS player_pets (
            id          SERIAL PRIMARY KEY,
            user_id     TEXT NOT NULL,
            pet_id      INTEGER NOT NULL,
            nickname    TEXT DEFAULT NULL,
            is_active   INTEGER DEFAULT 0,
            obtained_at TEXT DEFAULT (now()::text)
        )
    """)

    # Seeds
    c.execute("SELECT COUNT(*) FROM bosses")
    if c.fetchone()["count"] == 0:
        seed_bosses(c)

    c.execute("SELECT COUNT(*) FROM characters")
    if c.fetchone()["count"] == 0:
        seed_characters(c)

    c.execute("SELECT COUNT(*) FROM sagas")
    if c.fetchone()["count"] == 0:
        seed_sagas(c)
        seed_missions(c)

    c.execute("SELECT COUNT(*) FROM items")
    if c.fetchone()["count"] == 0:
        seed_items(c)

    c.execute("SELECT COUNT(*) FROM pets")
    if c.fetchone()["count"] == 0:
        seed_pets(c)

    conn.commit()
    conn.close()
    print("✅ Database initialized.")

def seed_bosses(c):
    bosses = [
        ("Afzal Khan",   "Adilshahi General",    8000,  550, 250, 400, 150, "The treacherous general of Bijapur Sultanate.", "Dark"),
        ("Shaista Khan", "Mughal Viceroy",        10000, 600, 300, 600, 200, "Aurangzeb's uncle stationed at Pune.", "Dark"),
        ("Aurangzeb",    "Mughal Emperor",        15000, 750, 400, 1000,350, "The cruel Mughal Emperor who waged war on Marathas for 27 years.", "Dark"),
        ("Siddi Jauhar", "Adilshahi Admiral",     7000,  500, 280, 350, 130, "The admiral who besieged Panhalgad fort.", "Water"),
        ("Jai Singh I",  "Rajput-Mughal General", 9000,  620, 350, 500, 180, "The Rajput general who forced the Treaty of Purandar.", "Fire"),
    ]
    c.executemany(
        "INSERT INTO bosses (name,title,hp,atk,def,reward_hon,reward_xp,description,element) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        bosses
    )

def seed_sagas(c):
    sagas = [
        (1,"Swarajya Saga",    "Shivaji's rise — from Torna Fort to the founding of the Maratha Empire.",1),
        (2,"Sinhagad Saga",    "Tanaji Malusare's legendary night assault to reclaim Sinhagad Fort.",1),
        (3,"Agra Escape Saga", "Shivaji's daring escape from Aurangzeb's captivity in Agra.",3),
        (4,"Rajyabhishek Saga","The grand coronation of Chhatrapati Shivaji Maharaj at Raigad.",5),
        (5,"Sambhaji Saga",    "Chhatrapati Sambhaji Maharaj's fearless reign and sacrifice.",8),
        (6,"Peshwa Saga",      "Bajirao I's legendary campaigns — never lost a single battle.",12),
    ]
    c.executemany(
        "INSERT INTO sagas (id,name,description,unlock_level) VALUES (%s,%s,%s,%s)",
        sagas
    )

def seed_missions(c):
    missions = [
        (1,1,"First Strike","Bijapur Scout",800,80,60,"Earth",80,40,0,"Repel the Bijapur scouts near Pune."),
        (1,2,"Torna Fort","Fort Guard",1200,100,80,"Earth",100,50,0,"Capture Torna Fort — Shivaji's first conquest."),
        (1,3,"Pratapgad Battle","Afzal's Soldier",1800,130,100,"Dark",150,70,0,"Defeat Afzal Khan's advance troops."),
        (1,4,"Killing of Afzal Khan","Afzal Khan (Weakened)",3000,200,130,"Dark",250,100,1,"Face Afzal Khan himself at Pratapgad!"),
        (2,1,"Night Infiltration","Mughal Sentry",1000,100,70,"Dark",90,45,0,"Sneak past Mughal sentries at night."),
        (2,2,"Wall Assault","Mughal Archer",1500,130,90,"Wind",120,60,0,"Scale the fort walls under arrow fire."),
        (2,3,"Gate Breach","Mughal Commander",2200,170,120,"Earth",180,80,0,"Break through the main gate."),
        (2,4,"Udaybhan Rathod","Udaybhan Rathod",4000,280,180,"Fire",300,120,1,"Face the Rajput commander defending Sinhagad!"),
        (3,1,"Under Surveillance","Mughal Guard",1500,140,100,"Dark",130,65,0,"Evade Mughal guards in Agra."),
        (3,2,"Sweet Box Ruse","Court Soldier",2000,160,120,"Earth",160,75,0,"Create a diversion using sweet boxes."),
        (3,3,"The Great Escape","Mughal Cavalry",2800,200,150,"Wind",220,95,0,"Outrun Mughal cavalry through enemy territory."),
        (3,4,"Return to Swarajya","Aurangzeb's General",5000,320,200,"Dark",400,150,1,"Fight off Aurangzeb's pursuing army!"),
        (4,1,"Raigad Preparation","Rival Sardar",2000,160,120,"Earth",150,70,0,"Quell internal rivalries before the coronation."),
        (4,2,"Coastal Defense","Portuguese Soldier",2500,190,140,"Water",190,85,0,"Repel Portuguese interference from the coast."),
        (4,3,"Coronation Guard","Mughal Assassin",3200,230,160,"Dark",250,110,0,"Stop the Mughal assassination attempt."),
        (4,4,"Jay Shivaji!","Jai Singh's Forces",6000,380,250,"Fire",500,200,1,"Final battle — secure the coronation!"),
        (5,1,"Sambhaji's Reign","Mughal Vanguard",2500,200,150,"Dark",200,90,0,"Defend Swarajya against Mughal advances."),
        (5,2,"Burhanpur Raid","Mughal City Guard",3000,230,170,"Fire",240,110,0,"Raid Burhanpur deep in Mughal territory."),
        (5,3,"Betrayal at Sangameshwar","Ganoji Shirke",3800,280,200,"Dark",300,130,0,"Stop the traitor who betrayed Sambhaji."),
        (5,4,"Sambhaji's Defiance","Mukarrab Khan",7000,430,280,"Dark",600,220,1,"Sambhaji refuses to bow — fight to the end!"),
        (6,1,"Malwa Campaign","Mughal Sardar",3000,240,180,"Earth",250,110,0,"Bajirao leads the Malwa campaign."),
        (6,2,"Vasai Fort Battle","Portuguese General",3800,280,210,"Water",300,140,0,"Capture Vasai Fort from the Portuguese."),
        (6,3,"Delhi Raid","Mughal Imperial Guard",5000,350,250,"Dark",400,170,0,"Bajirao's lightning raid near Delhi gates!"),
        (6,4,"Battle of Bhopal","Nizam-ul-Mulk",8000,500,320,"Wind",700,250,1,"The decisive Battle of Bhopal — Bajirao's masterpiece!"),
    ]
    c.executemany(
        """INSERT INTO missions
           (saga_id,mission_num,name,enemy_name,enemy_hp,enemy_atk,enemy_def,
            enemy_element,reward_hon,reward_xp,reward_keys,description)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        missions
    )

def seed_characters(c):
    characters = [
        ("Chhatrapati Shivaji Maharaj","L","Fire",5000,500,400,"The founder of the Maratha Empire.","hindavi","Bhavani Sword Strike",520,"Guerrilla Warfare",400,"Saffron Rage",600,"Jay Shivaji!",750),
        ("Bajirao I","L","Wind",4500,520,350,"Greatest Peshwa, never lost a battle.","hindavi","Cavalry Charge",500,"Lightning March",420,"Bhopal Slash",580,"Peshwa's Wrath",720),
        ("Chhatrapati Sambhaji Maharaj","L","Dark",4800,490,380,"Fearless son of Shivaji.","hindavi","Dark Resolve",480,"Burhanpur Raid",440,"Undying Spirit",560,"Chhatrapati's Fury",700),
        ("Tarabai","L","Light",4200,460,420,"Regent Queen who defied Aurangzeb.","hindavi","Queen's Guard",450,"Swarajya's Light",400,"Royal Command",540,"Bhavani's Blessing",680),
        ("Tanaji Malusare","E","Fire",3200,380,300,"The Lion of Sinhagad.","swarajya","Ghorpad Climb",360,"Night Strike",300,"Sinhagad Charge",420,"Lion's Sacrifice",520),
        ("Murarbaji Deshpande","E","Earth",3000,360,320,"Held Purandar fort against the Mughals.","swarajya","Fort Defense",340,"Stone Wall",380,"Counter Strike",400,"Purandar's Stand",500),
        ("Netaji Palkar","E","Wind",2800,370,290,"Senapati of Shivaji's cavalry.","swarajya","Wind Slash",350,"Cavalry Rush",310,"Swift Blade",390,"Senapati's Charge",480),
        ("Hambirrao Mohite","E","Water",3100,355,310,"Commander-in-chief under Sambhaji.","swarajya","River Rush",330,"Flood Strike",300,"Konkan Tide",370,"Commander's Wave",460),
        ("Mavla Soldier","R","Earth",1800,200,180,"Elite infantry soldier.","swarajya","Shield Bash",180,"Earth Strike",160,"Fortify",200,"Mavla Rush",240),
        ("Sardar Horseman","R","Wind",1600,220,160,"Swift cavalry of the Maratha forces.","swarajya","Hoof Strike",200,"Wind Dash",180,"Lance Charge",210,"Cavalry Slash",260),
        ("Peshwa Guard","R","Fire",1700,210,170,"Elite guard of the Peshwa court.","swarajya","Guard Strike",190,"Fire Jab",170,"Peshwa's Fist",220,"Blaze Slash",250),
        ("Konkan Scout","R","Water",1500,190,190,"Skilled scout from the Konkan coast.","swarajya","Scout Slash",170,"Mist Step",190,"Water Dart",200,"Coastal Strike",230),
        ("Foot Soldier","C","Earth",800,90,80,"Basic infantry of the Swarajya.","swarajya","Basic Strike",80,"Block",70,"Thrust",90,"War Cry",110),
        ("Village Warrior","C","Fire",750,95,75,"Brave villager who joined Shivaji's cause.","swarajya","Torch Swing",85,"Fire Punch",75,"Brave Slash",95,"Village Fury",115),
        ("River Guard","C","Water",700,85,90,"Guards the river crossings of Maharashtra.","swarajya","River Slash",75,"Splash",80,"Current Strike",85,"Flood Push",105),
        ("Hill Ranger","C","Wind",720,100,70,"Ranger who knows every Sahyadri path.","swarajya","Wind Cut",90,"Quick Step",70,"Hill Charge",100,"Sahyadri Gust",120),
    ]
    c.executemany(
        """INSERT INTO characters
           (name,rarity,element,base_hp,base_atk,base_def,description,banner,
            move1_name,move1_power,move2_name,move2_power,
            move3_name,move3_power,move4_name,move4_power)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        characters
    )

def seed_items(c):
    items = [
        ("Bhavani Sword","weapon","L",120,0,0,"The sacred sword of Chhatrapati Shivaji Maharaj.",5000),
        ("Peshwa's Talwar","weapon","E",85,0,0,"The razor-sharp sword of Bajirao I.",2500),
        ("Sardar's Lance","weapon","R",55,0,0,"A cavalry lance used by Maratha sardars.",1000),
        ("Mavla Katar","weapon","C",30,0,0,"A simple but effective push dagger.",300),
        ("Shivaji's Armour","armor","L",0,110,200,"The legendary armour of Chhatrapati Shivaji.",5000),
        ("Peshwa Kavach","armor","E",0,75,150,"The ceremonial armour of the Peshwa court.",2500),
        ("Maratha Chainmail","armor","R",0,50,100,"Standard chainmail worn by Maratha soldiers.",1000),
        ("Leather Vest","armor","C",0,25,50,"Basic leather protection for foot soldiers.",300),
        ("Royal Shirastra","helmet","L",0,90,150,"The royal helmet of Maratha royalty.",4000),
        ("Sardar's Turban","helmet","E",0,60,100,"A battle-hardened turban worn by sardars.",2000),
        ("Iron Helmet","helmet","R",0,40,70,"A basic iron helmet for battlefield protection.",800),
        ("Cloth Pagdi","helmet","C",0,20,40,"A simple cloth headwrap.",200),
    ]
    c.executemany(
        "INSERT INTO items (name,type,rarity,atk_bonus,def_bonus,hp_bonus,description,cost_hon) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        items
    )

def seed_pets(c):
    pets = [
        ("Shyamkarna","horse","L",80,60,300,"Shivaji's legendary black horse, swift as the wind.","🐴"),
        ("Krishnadevi","horse","E",55,40,200,"A brave war horse of the Maratha cavalry.","🐴"),
        ("Maratha Mare","horse","R",35,25,120,"A reliable cavalry horse.","🐎"),
        ("Village Horse","horse","C",20,15,70,"A simple but sturdy horse.","🐎"),
        ("Airawat","elephant","L",100,90,500,"A mighty war elephant that charges through enemy lines.","🐘"),
        ("Gajraj","elephant","E",70,65,350,"A trained war elephant of the Maratha forces.","🐘"),
        ("Fort Tusker","elephant","R",45,45,200,"A strong elephant used to break fort gates.","🐘"),
        ("Neelkantha","hawk","L",90,30,150,"A sacred blue-throated hawk, messenger of Shiva.","🦅"),
        ("Sahyadri Hawk","hawk","E",60,20,100,"A swift hawk that scouts enemy positions.","🦅"),
        ("River Falcon","hawk","R",40,15,70,"A falcon trained by Konkan scouts.","🦆"),
        ("Waghoba","tiger","L",130,50,250,"The sacred tiger spirit of Maharashtra.","🐯"),
        ("Sahyadri Tiger","tiger","E",90,35,180,"A fierce tiger from the Sahyadri ranges.","🐯"),
    ]
    c.executemany(
        "INSERT INTO pets (name,type,rarity,atk_bonus,def_bonus,hp_bonus,description,emoji) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        pets
    )
