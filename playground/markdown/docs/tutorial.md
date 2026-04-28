# Tutorial

Learn to use the project API from scratch.

## Getting Started

Install the client library:

```bash
pip install example-client
```

Set your credentials:

```bash
export API_TOKEN="your-token-here"
```

Verify connectivity:

```python
import example_client
client = example_client.Client(token=os.environ["API_TOKEN"])
print(client.ping())
```

## First Request

Fetch the item list with the client:

```python
items = client.items.list()
for item in items:
    print(item.name)
```

Pagination is automatic — the client fetches pages until the list is exhausted.

## Advanced Usage

Create and tag items programmatically:

```python
item = client.items.create(name="widget", tags=["new", "example"])
print(item.id)
```

Update an item's tags:

```python
client.items.update(item.id, tags=["updated"])
```
