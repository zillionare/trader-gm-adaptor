# zillionare-gm-adaptor

## 安装
1. 在windows机器上安装[https://emt.eastmoneysec.com/down](https://emt.eastmoneysec.com/down)，下载并安装第二个软件：
![](https://images.jieyu.ai/images/2023/03/20230403154605.png)

2. 在同一台机器上安装conda，推荐安装miniconda，并创建虚拟运行环境（python版本3.8）：
   ```
   conda create -n gmclient python=3.8
   ```
3. 安装gmadaptor:
    ```
    pip install gmadaptor-1.1.3-py3-none-any.whl
    ```
## 申请权限
请加入东方财富量化仿真交流群：971584613 ，找管理员申请开通量化实盘权限。请先看群置顶文件。
开通的主要门槛是要求100万初始资金。开通后可以撤资。

## 模拟和测试
在等待实盘权限开通的过程中，可以通过 https://emt.18.cn/apply/test-apply-client 开通模拟账号，先把程序和配置调通。

申请后，记录普通资金账号和密码，如下图：

![](https://images.jieyu.ai/images/2023/04/仿真.jpg)

在登录界面中，选择仿真交易：

![](https://images.jieyu.ai/images/2023/04/login.jpg)

登录后，界面显示如下：

![](https://images.jieyu.ai/images/2023/04/20230403200024.png)

### 配置账号
以下步骤对实盘和模拟盘均有效。

#### gmadaptor的配置文件
需要将量化软件中的实盘账号配置到gmadaptor的配置文件中。在用户目录下，创建`gmadaptor/config`目录，放置以下文件：
```yaml
# defaults.yaml
log_level: INFO

server_info:
    port: 9000
    # client 使用这一token来访问 gmadaptor 提供的服务
    access_token : "84ae0899-7a8d-44ff-9983-4fa7cbbc424b"

gm_info:
    fake: false
    # 文件单输出目录
    gm_output: "~/gmadaptor/FileOrders/out"
    trade_fees:
        commission: 2.5
        stamp_duty: 10.0
        transfer_fee: 0.1
        minimum_cost: 5.0
    accounts:
        # 账号名
        - name: fileorder_s01
          acct_id: 1a66e81c-ae5d-11ec-aef5-00163e0a4100
          # 文件单输入目录。东财量化终端将从这里读取文件单
          acct_input: "~/gmadaptor/FileOrders/inputs/fileorder_s01"
```
上述配置中，access_token 可任意指定，任何要访问此服务的客户端，必须持有此 token。

gm_output/acct_input 文件设置后，如果未创建，gmadaptor 将在启动时自动创建，请确保 gmadaptor 有权限读写这些文件夹。

accounts > name 中的值来自于在 EMC 终端中，您创建文件单输入时，指定的名称，见下图中的序号2：

![](https://images.jieyu.ai/images/2023/04/20230403194653.png)

accounts > acct_id 来自于下面序号3的位置，点击`ID`即可复制：

![](https://images.jieyu.ai/images/2023/04/20230403195425.png)

#### 配置EMC

在 量化 > 文件单 > 文件单输出 中，对下图中的 4，5，6，7 进行配置。其中4选择我们在上面配置文件中gm_output中设置的路径；5选择`csv`作为输出格式；6选择自动启动；7将所有项目全选中。

![](https://images.jieyu.ai/images/2023/04/output.jpg)

在 量化 > 文件单 > 文件单输入 中，对下图中的 3和4进行配置。其中3选择我们在上面配置文件中设置的 acct_input 路径，4选择自动启动。

![](https://images.jieyu.ai/images/2023/04/input.jpg)


### 模拟运行

在前面生成的gmclient虚拟环境中，执行以下命令，以启动gmadaptor服务器：
```
python -m gmadaptor.server
```
如果出现如下界面，表明服务器启动成功：

![](https://images.jieyu.ai/images/2023/04/started.jpg)

此时我们另开一个`conda`窗口，同样使用`gmclient`的虚拟环境，通过以下命令进行测试:
```
python -m gmdemo.test run %account %token %server %port
```

这里的account即 gmadaptor配置文件中的 gm_info > accounts > account_id, token 即server_info > access_token

这里的 server 即gmadaptor 所在的机器IP， port为端口。如果不提供，默认地，这两项分别为localhost和9000。

如果配置正常，这将打印出初始账号资金，当前持仓，和一笔买、卖的信息。
## 运行和维护

另外启动一个计划任务，在每天早上8:45左右启动EMC。
### 启动
使用下面的脚本来启动：
```
@echo off
call C:\ProgramData\Anaconda3\Scripts\activate.bat C:\ProgramData\anaconda3
call conda activate gmclient
python -m gmadaptor.server
pause
```

### 每日维护
EMC量化终端有时候不稳定。我们可以通过定时重启来提高起稳定性。通过以下代码，在盘后退出EMC：
```
REM kill process
TASKKILL /F /IM EMCTrade.exe

REM sleep 5 seconds
TIMEOUT  /T 5

REM remove all file orders after process killed

DEL /Q C:\zillionare\FileOrders\real_input\*.csv
```

# 客户端请求

客户端通过 http request来请求gmadaptor：

## 资产表
```python
# 请求资金信息
import httpx
headers = {
    "Authorization": "84ae0899-7a8d-44ff-9983-4fa7cbbc424b",
    "Account-ID": "780dc4fda3d0af8a2d3ab0279bfa48c9"
}

_url_prefix = "http://192.168.100.100:9000/"

def get_balance():
    r = httpx.post(_url_prefix + "balance", headers=headers)
    if r.status_code == 200:
        print("\n------ 账户资金信息 ------")
        print(r.json())
```
在上述代码中，有一些写法是所有功能中都通用的，比如，我们通过headers来传递鉴权信息。

此外，我们使用的是post方法，gmadaptor所有的方法都只响应post请求。如果请求成功完成，则返回代码是200。

## 持仓表
```python
def get_positions():
    r = httpx.post(_url_prefix + "positions", headers=headers)
    
    if r.status_code == 200:
        print("\n----- 持仓信息 ------")
        print(r.json())
```


