# 人際關係座標圖

這是一個使用 Python 與 Streamlit 製作的朋友比較工具。

使用者透過智慧排序比較，分別回答：

- 跟誰比較熟？
- 誰的人品更好？

程式會計算熟悉度與好感度，將每個人放到二維座標圖中。

## 目前版本狀態

程式已同時支援兩種模式：

- 本機模式：不需登入，結果保存在自己的 `results.json`。
- 雲端模式：使用 Google 登入，每位使用者的結果分開存到
  Supabase，適合部署後把固定網址分享給朋友。

雲端模式不會把名字、分數或座標放在網址中。資料庫只保存使用者
ID 的雜湊值，不保存 Google 密碼。

目前程式已完成雲端功能，但必須先完成本文件的「第一次公開部署」
設定，才會產生可以分享的網址。

## 安裝

第一次使用時，在 VS Code Terminal 執行：

```bash
python3 -m pip install -r college_pro_app/requirements.txt
```

主要套件：

- Streamlit：網頁介面
- Matplotlib：靜態座標圖
- Streamlit Components v2：可拖曳座標圖

## 啟動網站

### 方法一：VS Code 一鍵啟動

1. 在 VS Code 開啟 `college_pro_app/start_app.py`。
2. 點右上角的 ▶️ Run Python File。
3. 等待瀏覽器自動開啟。

如果瀏覽器沒有自動開啟，手動進入：

```text
http://localhost:8501
```

### 方法二：Terminal 啟動

在 `python練習` 資料夾執行：

```bash
python3 -m streamlit run college_pro_app/app.py --server.address localhost
```

## 關閉網站

回到正在執行 Streamlit 的 Terminal，按：

```text
Control + C
```

網站關閉後，已完成並保存的結果仍會保留。

## 使用流程

### 加到手機主畫面

這個版本可以像 App 一樣放在手機主畫面，仍需連上網路才能使用。請先開啟專用安裝頁：

```text
https://chengyunhou3-bit.github.io/friendship_map/
```

- iPhone／iPad：用 Safari 開啟安裝頁，點「分享」→「加入主畫面」。
- Android：用 Chrome 開啟安裝頁，點右上角選單 →「加到主畫面」或「安裝應用程式」。

安裝後會使用專案專屬圖示，點擊即可直接開啟網站。
如果手機第一次從主畫面開啟時仍停在安裝頁，點一次「開啟網站」即可；之後會直接進入 App。

### 建立新評分

1. 輸入至少兩個不同名字。
2. 點擊「開始比較」。
3. 完成熟悉度比較。
4. 完成好感度比較。
5. 查看排名、座標與圖表。

比較只有一套智慧流程，不需要選擇模式。程式會先縮小人物可能
落點的區間，只在位置尚未確定時繼續追問；能由既有答案推論的
關係不會重複詢問。人數越多，省下的題目越明顯；選擇「一樣」
時，兩人會保留在同一排名群組。

排序完成後，程式會用確定的先後關係推算原本全配對的分數。只要
使用者的判斷可以形成一致排序，最終排名、原始分數與座標會等同
於逐一完成所有配對。熟悉度與好感度是兩個不同問題，同一組名字
仍可能在兩個階段各出現一次。畫面顯示的是依目前作答路徑計算的
估計題數，實際題數可能更少。

如果選錯，點擊「← 回上一題」即可撤銷上一個答案並重新
選擇。從熟悉度切換到好感度後，以及剛進入結果頁時，也可以回
上一題。

使用電腦時也可以直接用鍵盤作答：

- `←` 或 `A`：選左邊人物
- `↓` 或 `S`：選「一樣」
- `→` 或 `D`：選右邊人物

按住按鍵不會連續回答多題。

名字可以一行一個，也可以用逗號分隔：

```text
Amy
Kevin
Leo
```

### 保存與載入多份紀錄

建立新評分時，可以替紀錄命名，例如「大學朋友」。完成後，左側
選單會列出所有已保存紀錄；選取一份後點擊：

```text
檢視選取紀錄
```

第一次載入既有紀錄時，可以選擇是否啟用 PIN。選擇不使用 PIN
會直接載入，之後也不再詢問；選擇使用 PIN 則需建立並確認一組
4～8 位數字。之後每次載入都必須輸入正確 PIN。有 PIN 的紀錄會
在清單顯示 🔒。側邊欄的「管理選取紀錄」可以啟用、關閉或更改
PIN；先點「調整 PIN」才會展開相關欄位，更改及關閉時必須先輸
入目前 PIN。資料只保存加鹽雜湊，不
會保存原始 PIN；如果忘記 PIN，目前仍只能刪除後重做。

每份紀錄會分開保存。拖曳座標、新增人物或編輯名字時，只會更新
目前開啟的紀錄。側邊欄的「管理選取紀錄」可以更改名稱或刪除
單獨一份。

進入結果頁後，點擊上方的「← 回到主頁」即可回到紀錄清單與新
紀錄輸入畫面，不會刪除剛才查看的內容。

### 新增人物

在結果頁的「➕ 新增人物」區域：

1. 輸入一個或多個新名字。
2. 點擊「加入並比較新人物」。
3. 只需完成包含新人物的配對。

舊人物彼此不需要重新比較。

### 編輯名字與座標

在「✏️ 編輯名字與座標」表格中，可以修改：

- 名字
- X 座標
- Y 座標

熟悉度與好感度原始分數為唯讀。

修改後點擊「套用名字與座標修改」，資料會更新並保存。

### 拖曳人物座標

在「🖐️ 拖曳調整座標」中：

1. 按住代表人物的圓點。
2. 拖曳到新的位置。
3. 放開滑鼠或手指。

新座標會自動保存。拖曳只修改 X/Y，不修改原始問答分數。
座標圖上方會顯示目前設定的畫面標題。

### 自訂標題與問題

點擊畫面標題右側的 ⚙️，可以修改：

- 畫面標題
- 第一組與第二組選擇題文字
- X 軸與 Y 軸標題

自訂文字會儲存在該使用者自己的結果中，不會影響其他
使用者。點擊「恢復預設」即可變回原本的朋友評分文字。

## 資料儲存

本機模式的永久結果保存在：

```text
college_pro_app/results.json
```

內容包含：

- 保存時間
- 紀錄名稱與多份紀錄清單
- 人物名字
- 熟悉度原始分數
- 好感度原始分數
- X 座標
- Y 座標

本機模式限制：

- 尚未完成的問卷只存在 Streamlit Session State。
- 中途關閉網站可能失去未完成的作答進度。
- JSON 沒有加密；能存取這個 Mac 帳號與資料夾的人仍能讀取。

雲端模式會把每位使用者的紀錄庫存入 Supabase 的
`friendship_results` 資料表：

- 每個 Google 帳號只能透過網站讀寫自己的結果。
- 網站伺服器使用雜湊後的使用者 ID 區分資料。
- Supabase 的私密金鑰只放在 Streamlit Secrets。
- 使用者可以刪除單獨一份紀錄，或刪除自己的全部雲端紀錄。
- 同一帳號可以保存並選取多份結果。

## 隱私原則

本專案的結果預設只允許建立結果的使用者查看。

本機模式透過以下方式維持隱私：

- 伺服器只綁定 `localhost`。
- 不提供公開結果網址。
- 不把名字或分數放在網址中。
- 不上傳評分資料到外部 API。
- Git 忽略私人 JSON 資料。

雲端模式透過以下方式維持隱私：

- 未登入時不顯示問卷或結果。
- 每份資料都綁定登入者的使用者 ID。
- 不提供公開結果分享網址。
- 資料表拒絕瀏覽器直接存取，只能由網站伺服器存取。
- `secrets.toml` 已加入 `.gitignore`，不可上傳 GitHub。

## 第一次公開部署

公開版使用 Streamlit Community Cloud、Supabase Free 與 Google
登入，可以從每月 US$0 開始。

部署需要建立三個免費帳號或專案：

1. GitHub：保存可公開部署的程式碼。
2. Supabase：保存每位使用者自己的結果。
3. Google Cloud：提供 Google 登入。

### 1. 建立 Supabase 資料庫

1. 登入 Supabase 並建立 Free project。
2. 打開 SQL Editor。
3. 複製 `supabase_schema.sql` 的全部內容並執行。
4. 在 Project Settings 的 API 頁面保存：
   - Project URL
   - `service_role` key

`service_role` key 是私密金鑰，不能傳給朋友、貼到聊天室或上傳
GitHub。

### 2. 將程式放上 GitHub

建立一個新的 GitHub repository，再將本資料夾中的程式碼上傳。
上傳前確認檔案清單中沒有：

```text
results.json
.streamlit/secrets.toml
```

`.streamlit/secrets.example.toml` 是安全的格式範例，可以上傳。

### 3. 先部署 Streamlit 網站

1. 登入 `share.streamlit.io`。
2. 選擇 GitHub repository。
3. Main file path 選擇 `app.py`；若上傳的是整個 `python練習`
   repository，則選擇 `college_pro_app/app.py`。
4. 先取得網站的 `https://...streamlit.app` 網址。

### 4. 建立 Google 登入

1. 在 Google Cloud 建立 project。
2. 建立 OAuth Web application。
3. Authorized redirect URI 填入：

```text
https://你的網址.streamlit.app/oauth2callback
```

4. 保存 Google 提供的 Client ID 與 Client Secret。

### 5. 填入 Streamlit Secrets

打開 Streamlit 網站的 Settings → Secrets，依照
`.streamlit/secrets.example.toml` 填入：

- 網站 redirect URI
- 隨機 cookie secret
- Google Client ID 與 Client Secret
- Supabase Project URL 與 `service_role` key

保存並重新啟動網站。看到「使用 Google 登入」就表示雲端模式已
開啟。

## 分享給朋友

完成第一次部署後，只需把 `https://...streamlit.app` 網址傳給
朋友。朋友的操作方式是：

1. 開啟網址。
2. 使用自己的 Google 帳號登入。
3. 建立並保存自己的朋友評分。
4. 下次用同一個 Google 帳號登入，即可從清單選取以前的結果。

朋友不需要安裝 Python、下載程式碼或建立 Supabase 帳號。

### 訪客模式

不想登入的使用者可點擊「以訪客身分使用」：

- 可使用完整的比較、圖表、拖曳、新增人物與自訂文字功能。
- 資料只保留在當次 Streamlit 工作階段。
- 不寫入 Supabase，也不會出現在其他使用者的紀錄中。
- 關閉分頁、工作階段失效或網站重啟後，無法載入上次結果。

使用 Google 登入的使用者仍會保留原本的私人雲端儲存功能。

## 專案檔案

```text
college_pro_app/
├── app.py             # Streamlit 網頁主程式
├── cloud_store.py     # 每位使用者的 Supabase 雲端儲存
├── draggable_map.py   # 可拖曳座標圖元件
├── friendship.py      # 比較、計分、保存與 Terminal 版
├── start_app.py       # 一鍵啟動網站
├── supabase_schema.sql # 建立雲端資料表
├── requirements.txt   # Python 套件
├── results.json       # 私人結果，不可上傳
└── README.md          # 使用手冊
```

## 問題排除

### 網址打不開

確認 `start_app.py` 或 Streamlit 指令仍在 Terminal 中執行。

### 顯示連接埠已被使用

可能已有一個網站正在執行。先開啟：

```text
http://localhost:8501
```

若仍有問題，回到舊 Terminal 按 `Control + C`，再重新啟動。

### 修改程式後畫面沒有更新

重新整理瀏覽器。如果仍未更新，關閉 Streamlit 後重新啟動。
