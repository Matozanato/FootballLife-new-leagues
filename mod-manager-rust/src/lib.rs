//! fl27mm core — everything the CLI and the desktop UI share.
//!
//! Sider's two ordering rules are the whole problem this crate addresses:
//! `cpk.root` is first-wins, so pack order decides which content the game
//! actually sees, and `lua.module` loads in sequence, so dependencies must
//! precede their users. Both are invisible in the file itself, which is why a
//! hand-edited ini silently disables packs.
//!
//! The format modules (`cpk`, `utf`, `ftex`, `wesys`, `pesdb`) are the mod-maker
//! half: they read and write the game's own containers rather than shelling out
//! to third-party tools.

pub mod ask;
pub mod assets;
pub mod bc7;
pub mod binread;
pub mod conflict;
pub mod cpk;
pub mod crilayla;
pub mod fmdl;
pub mod foxfmt;
pub mod fpk;
pub mod frig;
pub mod fsutil;
pub mod ftex;
pub mod gamemap;
pub mod gani;
pub mod ini;
pub mod install;
pub mod menus;
pub mod order;
pub mod packs;
pub mod pesdb;
pub mod render;
pub mod structure;
pub mod studio;
pub mod utf;
pub mod wesys;
