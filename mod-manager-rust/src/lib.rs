//! fl27mm core: readers and writers for the game's own formats (CPK archives,
//! FTEX textures, FMDL models, GANI animations, skeletons and rigs, PES tables,
//! WESYS containers, compiled menus and menu flow files), shared by the command
//! line and the optional PyO3 module FL Mod Studio loads.
//!
//! Nothing here touches sider.ini. Pack order, modules and installs belong to
//! FL Mod Studio itself, which keeps restore points for every change.

pub mod bc7;
pub mod assets;
pub mod ask;
pub mod binread;
pub mod crilayla;
pub mod cpk;
pub mod fmdl;
pub mod fpk;
pub mod frig;
pub mod render;
pub mod foxfmt;
pub mod fsutil;
pub mod ftex;
pub mod gani;
pub mod gamemap;
pub mod install;
pub mod menus;
pub mod pesdb;
pub mod structure;
pub mod utf;
pub mod wesys;