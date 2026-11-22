//! sider.ini reading and writing that preserves what it did not change.
//!
//! Sider's ini is order-sensitive in two places: `cpk.root` is searched first
//! to last and the first pack carrying a file wins, and `lua.module` lines load
//! in sequence so dependencies must precede their users. A parser that
//! round-trips into a map and back would silently destroy both, so this keeps
//! every line -- comments, blanks, disabled entries, indentation -- and edits
//! only the entries it was asked to.

use std::fs;
use std::io;
use std::path::Path;

#[derive(Debug, Clone)]
pub struct Entry {
    pub indent: String,
    pub disabled: bool,
    pub key: String,
    pub value: String,
    /// Whether the source quoted this value. Sider accepts both, but rewriting
    /// `lua.enabled = 1` as `lua.enabled = "1"` is a change nobody asked for,
    /// and a round-trip that alters untouched lines cannot be trusted.
    pub quoted: bool,
    /// Trailing comment, kept verbatim including its leading whitespace.
    pub comment: String,
}

impl Entry {
    pub fn render(&self) -> String {
        let value = if self.quoted {
            format!("\"{}\"", self.value)
        } else {
            self.value.clone()
        };
        format!(
            "{}{}{} = {}{}",
            self.indent,
            if self.disabled { ";" } else { "" },
            self.key,
            value,
            self.comment
        )
    }
}

#[derive(Debug, Clone)]
pub enum Line {
    Raw(String),
    Entry(Entry),
}

#[derive(Debug, Clone, Default)]
pub struct Ini {
    pub lines: Vec<Line>,
    /// The line ending the file actually used. Sider accepts either, but
    /// rewriting a hand-edited file that used bare LF as CRLF changes every
    /// single line in it, and that is not what "only one line was touched"
    /// means. Detected on read, reproduced on write.
    pub crlf: bool,
}

/// Split `key = "value"  # comment`, tolerating unquoted values and either
/// comment marker. Returns None for anything that is not an assignment.
fn parse_assignment(text: &str) -> Option<(String, String, bool, String)> {
    let eq = text.find('=')?;
    let key = text[..eq].trim().to_string();
    if key.is_empty() || key.contains(char::is_whitespace) {
        return None;
    }
    let rest = text[eq + 1..].trim_start();
    let (value, quoted, comment) = if let Some(after) = rest.strip_prefix('"') {
        match after.find('"') {
            Some(end) => (after[..end].to_string(), true, after[end + 1..].to_string()),
            None => (after.to_string(), true, String::new()),
        }
    } else {
        // Unquoted: a comment marker ends the value.
        let cut = rest.find(['#', ';']).unwrap_or(rest.len());
        (
            rest[..cut].trim_end().to_string(),
            false,
            rest[cut..].to_string(),
        )
    };
    Some((key, value, quoted, comment))
}

impl Ini {
    pub fn parse(text: &str) -> Ini {
        let mut lines = Vec::new();
        for raw in text.lines() {
            let trimmed = raw.trim_start();
            let indent = &raw[..raw.len() - trimmed.len()];
            let (disabled, body) = match trimmed.strip_prefix(';') {
                Some(rest) => (true, rest.trim_start()),
                None => (false, trimmed),
            };
            if body.starts_with('#') || body.starts_with('[') || body.is_empty() {
                lines.push(Line::Raw(raw.to_string()));
                continue;
            }
            match parse_assignment(body) {
                Some((key, value, quoted, comment)) => lines.push(Line::Entry(Entry {
                    indent: indent.to_string(),
                    disabled,
                    key,
                    value,
                    quoted,
                    comment,
                })),
                None => lines.push(Line::Raw(raw.to_string())),
            }
        }
        // Mixed endings are normalised to whichever one the file leads with; a
        // file with no line breaks at all keeps the LF default.
        Ini {
            lines,
            crlf: text.contains("\r\n"),
        }
    }

    pub fn read(path: &Path) -> io::Result<Ini> {
        let text = fs::read_to_string(path)?;
        Ok(Ini::parse(&text))
    }

    pub fn render(&self) -> String {
        let mut out = String::new();
        for line in &self.lines {
            match line {
                Line::Raw(s) => out.push_str(s),
                Line::Entry(e) => out.push_str(&e.render()),
            }
            out.push_str(if self.crlf { "\r\n" } else { "\n" });
        }
        out
    }

    pub fn write(&self, path: &Path) -> io::Result<()> {
        fs::write(path, self.render())
    }

    /// Active entries for a key, in file order.
    pub fn active(&self, key: &str) -> Vec<&Entry> {
        self.lines
            .iter()
            .filter_map(|l| match l {
                Line::Entry(e) if e.key.eq_ignore_ascii_case(key) && !e.disabled => Some(e),
                _ => None,
            })
            .collect()
    }

    /// Every entry for a key, active or disabled, in file order.
    pub fn all(&self, key: &str) -> Vec<&Entry> {
        self.lines
            .iter()
            .filter_map(|l| match l {
                Line::Entry(e) if e.key.eq_ignore_ascii_case(key) => Some(e),
                _ => None,
            })
            .collect()
    }

    pub fn entries_mut(&mut self, key: &str) -> Vec<&mut Entry> {
        self.lines
            .iter_mut()
            .filter_map(|l| match l {
                Line::Entry(e) if e.key.eq_ignore_ascii_case(key) => Some(e),
                _ => None,
            })
            .collect()
    }

    /// Indices of the lines holding a key, so a reorder can move whole lines.
    pub fn line_indices(&self, key: &str) -> Vec<usize> {
        self.lines
            .iter()
            .enumerate()
            .filter_map(|(i, l)| match l {
                Line::Entry(e) if e.key.eq_ignore_ascii_case(key) => Some(i),
                _ => None,
            })
            .collect()
    }

    /// Replace the entries for a key with a new ordered list, keeping them at
    /// the position of the first one so surrounding settings do not move.
    pub fn replace_ordered(&mut self, key: &str, ordered: Vec<Entry>) {
        let idx = self.line_indices(key);
        let Some(&first) = idx.first() else { return };
        for i in idx.iter().rev() {
            self.lines.remove(*i);
        }
        for (offset, entry) in ordered.into_iter().enumerate() {
            self.lines.insert(first + offset, Line::Entry(entry));
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const SAMPLE: &str = "[sider]\r\nlua.enabled = 1\r\n\tcpk.root = \".\\livecpk\\A\"\r\n\tcpk.root = \".\\livecpk\\B\"  # second\r\n\t;lua.module = \"off.lua\"\r\n\tlua.module = \"on.lua\"\r\n";

    #[test]
    fn round_trips_every_line() {
        let ini = Ini::parse(SAMPLE);
        assert_eq!(ini.render(), SAMPLE);
    }

    #[test]
    fn order_is_preserved_and_disabled_excluded() {
        let ini = Ini::parse(SAMPLE);
        let packs: Vec<&str> = ini
            .active("cpk.root")
            .iter()
            .map(|e| e.value.as_str())
            .collect();
        assert_eq!(packs, vec![".\\livecpk\\A", ".\\livecpk\\B"]);
        let mods: Vec<&str> = ini
            .active("lua.module")
            .iter()
            .map(|e| e.value.as_str())
            .collect();
        assert_eq!(mods, vec!["on.lua"]);
        assert_eq!(ini.all("lua.module").len(), 2);
    }

    #[test]
    fn comments_survive_a_reorder() {
        let mut ini = Ini::parse(SAMPLE);
        let mut entries: Vec<Entry> = ini.all("cpk.root").into_iter().cloned().collect();
        entries.reverse();
        ini.replace_ordered("cpk.root", entries);
        let out = ini.render();
        assert!(out.find("livecpk\\B").unwrap() < out.find("livecpk\\A").unwrap());
        assert!(out.contains("# second"));
        assert!(out.contains("lua.enabled = 1"));
    }

    #[test]
    fn unquoted_and_hash_comments_parse() {
        let ini = Ini::parse("debug = 0\nname = thing # note\n");
        assert_eq!(ini.active("debug")[0].value, "0");
        assert_eq!(ini.active("name")[0].value, "thing");
        assert!(ini.active("name")[0].comment.contains("# note"));
    }
}
