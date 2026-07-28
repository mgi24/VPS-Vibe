# OpenCode Events Reference

Sumber: https://opencode.ai/docs/plugins/

## Sudah Di-Hook (discord-notify.js)

| Event/Hook | Deskripsi |
|---|---|
| `permission.asked` | Saat AI meminta izin untuk suatu aksi |
| `permission.replied` | Saat user mengizinkan/menolak izin |
| `session.created` | Session baru dimulai |
| `session.idle` | Session selesai/selesai bekerja |
| `session.error` | Session mengalami error |
| `tool.execute.after` | Setelah tool dieksekusi (digunakan untuk counter) |
| `tool.execute.before` | Sebelum tool dieksekusi (detect `question` tool) |

---

## Belum Di-Hook

### Command Events
| Event | Deskripsi | Potensi |
|---|---|---|
| `command.executed` | Command yang dieksekusi user | Notifikasi command penting |

### File Events
| Event | Deskripsi | Potensi |
|---|---|---|
| `file.edited` | File yang diedit oleh AI | Laporan file yang berubah |
| `file.watcher.updated` | File berubah (watcher) | Monitoring perubahan file |

### Session Events
| Event | Deskripsi | Potensi |
|---|---|---|
| `session.compacted` | Session di-compress (context penuh) | Info session di-compact |
| `session.status` | Status session berubah | Tracking status real-time |
| `session.diff` | Diff file yang berubah | Laporan perubahan file |
| `session.deleted` | Session dihapus | Info session dihapus |
| `session.updated` | Session di-update | Info update session |

### Tool Events
| Event | Deskripsi | Potensi |
|---|---|---|
| `tool.execute.before` | Sebelum tool dieksekusi | Catat tool + argumen yang dipanggil |

### Server Events
| Event | Deskripsi | Potensi |
|---|---|---|
| `server.connected` | OpenCode server terkoneksi | Notifikasi startup |

### Message Events
| Event | Deskripsi | Potensi |
|---|---|---|
| `message.updated` | Message di-update | Tracking pesan (noisy) |
| `message.removed` | Message dihapus | — |
| `message.part.updated` | Bagian message berubah | Terlalu detail |
| `message.part.removed` | Bagian message dihapus | Terlalu detail |

### Installation Events
| Event | Deskripsi | Potensi |
|---|---|---|
| `installation.updated` | OpenCode di-update | Notifikasi update versi |

### LSP Events
| Event | Deskripsi | Potensi |
|---|---|---|
| `lsp.client.diagnostics` | LSP diagnostics | Error/warning di code |
| `lsp.updated` | LSP server berubah | — |

### Todo Events
| Event | Deskripsi | Potensi |
|---|---|---|
| `todo.updated` | Todo list berubah | Tracking progress task |

### Shell Events
| Event | Deskripsi | Potensi |
|---|---|---|
| `shell.env` | Environment shell | Bukan untuk notifikasi |

### TUI Events (tidak relevan, kamu pakai web)
| Event | Deskripsi |
|---|---|
| `tui.prompt.append` | Prompt TUI |
| `tui.command.execute` | Command TUI |
| `tui.toast.show` | Toast notification TUI |

---

## Saran Untuk Ditambahkan

1. **`file.edited`** — Notifikasi file yang diedit AI (berguna untuk audit)
2. **`tool.execute.before`** — Catat tool apa yang akan dipanggil + argumennya
3. **`session.compacted`** — Info session di-compress (context management)
4. **`session.status`** — Tracking status session (thinking, processing, idle)
5. **`lsp.client.diagnostics`** — Notifikasi error/warning di codebase
