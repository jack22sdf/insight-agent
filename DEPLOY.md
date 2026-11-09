# 服务器部署：公开离线 + 密码保护在线

适用：一台 Linux 服务器、一个域名、一个 Streamlit 进程。需要安装 Git、Docker Engine 和 Compose 插件。服务器规格可先用 2 核 2 GB 试运行，容量需按实际访问测试。

## 1. 准备域名与端口

将域名 A 记录指向服务器公网 IPv4。仅在确实配置 IPv6 时添加 AAAA。云防火墙放行 TCP 80/443，SSH 仅允许管理员来源；不开放 8501。Caddy 自动申请 HTTPS 证书，应用仅在 Docker 内部网络可达。

## 2. 下载并准备配置

```bash
git clone https://github.com/jack22sdf/insight-agent.git
cd insight-agent
cp deploy.env.example deploy.env
cp server.env.example server.env
chmod 600 deploy.env server.env
```

编辑 `deploy.env`，将 DOMAIN 设置成自己的域名（不加 https://）。编辑 `server.env`，填入 DeepSeek Key。不要填写旧电脑上的 RAG_ENV_PATH。

## 3. 设置在线访问密码

```bash
docker compose --env-file deploy.env build
docker compose --env-file deploy.env run --rm --no-deps app python access_control.py
```

按提示输入至少 12 个字符的密码（建议使用密码管理器生成的随机密码），再次确认。程序只输出 `ONLINE_PASSWORD_HASH=...`，将整行复制到 server.env 对应位置。明文密码不写入仓库或容器配置。留空密码哈希时在线功能关闭。

`ONLINE_DAILY_LIMIT=20` 表示全站每天最多 20 个获准执行的在线任务；失败也占用配额。UTC 零点重置，不是北京时间零点。一次任务最多 5 次模型调用，所以它是任务数限制，不是人民币预算保证。

## 4. 启动与验证

```bash
docker compose --env-file deploy.env up -d
docker compose --env-file deploy.env ps
docker compose --env-file deploy.env logs --tail=50 app caddy
```

浏览器打开 `https://你的域名`：

1. 不输入密码，运行内置示例的离线分析；应显示净额 6150.00。
2. 取消“离线计算”，输入错误密码；应拒绝且不调用模型。
3. 输入正确密码；应运行 DeepSeek 分析。
4. 若密码未配置、任务忙碌或超过配额，应显示提示。

访客仍可以上传 CSV 做离线分析。公开离线功能也消耗服务器计算资源，因此本方案适合低流量演示，不是防 DDoS 或完整多租户平台。

## 5. 运维

修改密码哈希、Key 或每日额度后：

```bash
docker compose --env-file deploy.env up -d --force-recreate app
```

升级：

```bash
git pull --ff-only
docker compose --env-file deploy.env up -d --build
```

临时关闭在线：清空 server.env 中 ONLINE_PASSWORD_HASH 并重建 app 容器。计数写入 app_data 持久卷，正常重启不清零。不要删除持久卷来升级。

## 访问限制范围

- 在线密码每次执行都在服务端校验，未配置则拒绝。
- PBKDF2-SHA256 600000 轮、随机盐、常量时间比较。
- 全站固定 5 分钟窗口最多 30 次密码验证尝试；跨窗口边界可能短时出现两倍尝试。全局限额可能被恶意耗尽造成在线暂不可用。
- 单进程同时一个在线任务；本 Compose 不支持直接横向扩容。多副本应改用集中式配额和分布式锁。
- 全站每日默认 20 次在线任务，固定 UTC 日窗口，SQLite 事务防止配额竞态。
- 无账号体系或个人额度；共享密码用户共用配额。密码轮换后下次调用立即按新哈希校验。
- 本机已通过测试；实际服务器的域名、TLS 与网络需部署后按上述步骤验证。

官方参考：
- https://docs.streamlit.io/develop/api-reference/configuration/config.toml
- https://docs.docker.com/engine/install/ubuntu/
- https://caddyserver.com/docs/quick-starts/https
