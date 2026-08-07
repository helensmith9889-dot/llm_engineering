# Python — dict、`.get()`、f-string（对照 JS）

> 来源：`week2/day4_zh.ipynb` 里的 `ticket_prices` + `get_ticket_price`  
> 相关：[`基础语法.md`](基础语法.md)（字典方括号取值）

## 这段代码在干什么？

```python
ticket_prices = {"london": "$799", "paris": "$899", "tokyo": "$1400", "berlin": "$499"}

def get_ticket_price(destination_city):
    print(f"Tool called for city {destination_city}")
    price = ticket_prices.get(destination_city.lower(), "Unknown ticket price")
    return f"The price of a ticket to {destination_city} is {price}"
```

本地「查票价」工具：传入城市名 → 查字典 → 拼成一句自然语言返回。  
后面 LLM 的 **tool calling** 会调用这个函数，而不是真的上网查票。

---

## 1. `ticket_prices`：Python dict ≈ JS 对象

```python
ticket_prices = {"london": "$799", "paris": "$899"}
```

```js
const ticketPrices = { london: "$799", paris: "$899" };
```

| | Python `dict` | JavaScript 对象 |
|---|---|---|
| 取值 | `ticket_prices["london"]` | `ticketPrices["london"]` / `ticketPrices.london` |
| 键不存在 | **抛 `KeyError`** | 得到 `undefined`（一般不抛错） |

也可用 JS `Map`：

```js
const ticketPrices = new Map([["london", "$799"], ["paris", "$899"]]);
```

---

## 2. `.get(键, 默认值)`：安全取值

```python
price = ticket_prices.get(destination_city.lower(), "Unknown ticket price")
```

- `.lower()`：把 `"London"` 变成 `"london"`，和字典键一致  
- `.get(key, default)`：有键就返回值；没有就返回默认值，**不会**因缺键崩溃

对比方括号：

| 写法 | 键存在 | 键不存在 |
|------|--------|----------|
| `ticket_prices["paris"]` | `"$899"` | **`KeyError`** |
| `ticket_prices.get("paris", "未知")` | `"$899"` | `"未知"` |

### 对照 JS

普通对象**没有** `.get`（`Map` 才有）。常用：

```js
const city = destinationCity.toLowerCase();
const price = ticketPrices[city] ?? "Unknown ticket price";
```

| Python | JavaScript |
|---|---|
| `d[key]`（缺键会炸） | `obj[key]`（缺键 → `undefined`） |
| `d.get(key, default)` | `obj[key] ?? default` |
| `"London".lower()` | `"London".toLowerCase()` |
| `Map` 的 `.get` | `map.get(key) ?? default` |

`??` 是空值合并：左边是 `null` / `undefined` 时才用右边（`0`、`""` 不会被替换）。

---

## 3. `f"..."`：f-string（格式化字符串）

字符串前加 `f`，里面用 `{表达式}`，运行时把值嵌进去：

```python
destination_city = "London"
price = "$799"

print(f"Tool called for city {destination_city}")
# → Tool called for city London

return f"The price of a ticket to {destination_city} is {price}"
# → The price of a ticket to London is $799
```

等价旧写法：

```python
"Tool called for city " + destination_city
"Tool called for city {}".format(destination_city)
```

### 对照 JS 模板字符串

```js
console.log(`Tool called for city ${destinationCity}`);
return `The price of a ticket to ${destinationCity} is ${price}`;
```

| Python | JavaScript |
|---|---|
| `f"Hello {name}"` | `` `Hello ${name}` `` |
| 没有 `f` 时 `{name}` 只是普通文字 | 不用反引号时 `${name}` 也是普通文字 |
| 想输出真正的 `{` | 写 `{{` / `}}` | 模板字符串里较少需要转义 |

注意：没有 `f` 的普通字符串里写 `{destination_city}`，**不会**替换变量，只是原样字符。

---

## 4. 整段流程串起来

1. 调用 `get_ticket_price("London")`
2. `print(f"...")` 打日志（调试用）
3. `"London".lower()` → `"london"`
4. `ticket_prices.get("london", ...)` → `"$799"`
5. `return f"..."` → `"The price of a ticket to London is $799"`

模型拿到这句话后，再组织成对用户的回答。

---

## 小练习

1. 把 `.get(...)` 改成 `ticket_prices[destination_city.lower()]`，查一个不存在的城市会发生什么？
2. 用 JS 写出与 `get_ticket_price` 等价的函数（对象 + `??` + 模板字符串）。
3. 去掉 `f`，只写 `"Tool called for city {destination_city}"`，打印结果是什么？
