from datetime import datetime, timezone
import json
import os
import discord
from discord import app_commands
from discord.ext import commands, tasks

DATA_DIR = "/app/data" if os.path.isdir("/app/data") else "."
STATE_FILE = os.path.join(DATA_DIR, "scheduled_releases.json")
DEFAULT_ANNOUNCE_CHANNEL_ID = 1573672717733859368

SCHEDULED_UPDATES = [
    {
        "id": "pets_update_10_roster_2026_12_04",
        # Friday, Dec 4, 2026 at 10:00 AM GMT/UTC
        "release_at_utc": datetime(2026, 12, 4, 10, 0, tzinfo=timezone.utc),
        "channel_id": DEFAULT_ANNOUNCE_CHANNEL_ID,
        "title": "🐾 Starlight Sandbox Update • 10 Pets Progression Lineup!",
        "description": (
            "The 10-pet progression lineup is arriving for **Starlight Sandbox**! "
            "Build your companions from starter helpers to endgame void pets using your "
            "pet, egg, adventure, and high-tier progression loops—and share any balance "
            "or bug reports via `/feedback`."
        ),
        "fields": [
            {
                "name": "✨ Early & Mid Companions (CD Reduction + Perks)",
                "value": (
                    "• **Shadow Mouse** (`-1%` CD)\n"
                    "• **Mossy Badger** (`-3%` CD, `+5%` gathering yield)\n"
                    "• **Tidepool Crab** (`-4%` CD, `+8%` fish/pearl drop chance)\n"
                    "• **Sunbeam Fox** (`-6%` CD, `+5%` coin payout)\n"
                    "• **Glimmer Owl** (`-7%` CD, `+5%` XP gain)"
                ),
                "inline": False,
            },
            {
                "name": "🌟 Upper, Mythic & Void Companions",
                "value": (
                    "• **Cinder Lynx** (`-9%` CD, `+3%` crit chance)\n"
                    "• **Starlight Celestial Spirit** (`-10%` CD)\n"
                    "• **Tempest Drake** (`-12%` CD, `+8%` coins & `+5%` XP)\n"
                    "• **Aether Phoenix** (`-14%` CD, `+5%` crit & HP recovery boost)\n"
                    "• **Singularity Kitsune** (`-15%` CD, `+6%` crit & `+10%` rare drop chance)"
                ),
                "inline": False,
            },
        ],
    },
]


def _load_posted_ids() -> set[str]:
  if not os.path.exists(STATE_FILE):
    return set()
  try:
    with open(STATE_FILE, "r", encoding="utf-8") as f:
      data = json.load(f)
    posted = data.get("posted", []) if isinstance(data, dict) else []
    return {str(item) for item in posted}
  except (OSError, json.JSONDecodeError):
    return set()


def _save_posted_ids(posted_ids: set[str]) -> None:
  os.makedirs(os.path.dirname(STATE_FILE) or ".", exist_ok=True)
  with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump({"posted": sorted(posted_ids)}, f, indent=2)


def build_release_embed(entry: dict) -> discord.Embed:
  embed = discord.Embed(
      title=entry["title"],
      description=entry["description"],
      color=0x00F0FF,
      timestamp=discord.utils.utcnow(),
  )
  for field in entry.get("fields", []):
    embed.add_field(
        name=field["name"],
        value=field["value"],
        inline=field.get("inline", False),
    )
  embed.set_footer(
      text="Rebel Vibez Gaming • Starlight Sandbox • Use /feedback for reports"
  )
  return embed


class ReleaseSchedulerCog(commands.Cog):

  def __init__(self, bot):
    self.bot = bot
    self.check_scheduled_updates.start()

  def cog_unload(self):
    self.check_scheduled_updates.cancel()

  async def _post_entry(self, entry: dict) -> bool:
    channel_id = entry.get("channel_id") or DEFAULT_ANNOUNCE_CHANNEL_ID
    if not channel_id:
      return False

    channel = self.bot.get_channel(channel_id)
    if channel is None:
      try:
        channel = await self.bot.fetch_channel(channel_id)
      except discord.HTTPException:
        return False

    if channel is None:
      return False

    embed = build_release_embed(entry)
    await channel.send(embed=embed)
    return True

  @tasks.loop(minutes=5)
  async def check_scheduled_updates(self):
    now_utc = discord.utils.utcnow()
    posted_ids = _load_posted_ids()
    changed = False

    for entry in SCHEDULED_UPDATES:
      release_id = str(entry["id"])
      if release_id in posted_ids:
        continue

      release_at = entry["release_at_utc"]
      if release_at.tzinfo is None:
        release_at = release_at.replace(tzinfo=timezone.utc)

      if now_utc >= release_at:
        sent = await self._post_entry(entry)
        if sent:
          posted_ids.add(release_id)
          changed = True

    if changed:
      _save_posted_ids(posted_ids)

  @check_scheduled_updates.before_loop
  async def before_check_scheduled_updates(self):
    await self.bot.wait_until_ready()

  @app_commands.command(
      name="releases",
      description="Owner only: View scheduled and posted Starlight Sandbox update announcements.",
  )
  async def releases(self, interaction: discord.Interaction):
    if not await self.bot.is_owner(interaction.user):
      await interaction.response.send_message(
          "❌ Only the bot owner can view the release schedule.",
          ephemeral=True,
      )
      return

    posted_ids = _load_posted_ids()
    lines = []
    for entry in SCHEDULED_UPDATES:
      rid = str(entry["id"])
      dt = entry["release_at_utc"]
      if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
      status = "✅ Posted" if rid in posted_ids else "⏳ Scheduled"
      lines.append(f"{status} • `{rid}` — <t:{int(dt.timestamp())}:F>")

    embed = discord.Embed(
        title="🗓️ Starlight Sandbox Release Queue",
        description="\n".join(lines)
        if lines
        else "No updates configured in `SCHEDULED_UPDATES`.",
        color=0x00F0FF,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
  await bot.add_cog(ReleaseSchedulerCog(bot))
