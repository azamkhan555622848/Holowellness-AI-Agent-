### Build sqlite-vec on Ubuntu 22.04 ARM64 (t4g.small)

```bash
sudo apt update && sudo apt install -y build-essential git sqlite3 libsqlite3-dev
cd /opt
sudo git clone https://github.com/asg017/sqlite-vec.git
cd sqlite-vec
sudo make
sudo mkdir -p /opt/sqlite-vec
sudo cp dist/linux-aarch64/sqlite-vec0.so /opt/sqlite-vec/
sudo chmod 644 /opt/sqlite-vec/sqlite-vec0.so
```

At runtime set: `SQLITE_VEC_SO_PATH=/opt/sqlite-vec/sqlite-vec0.so`.

