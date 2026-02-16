from langchain_core.messages import convert_to_messages


def pretty_print_message(message, indent=False):
    pretty_message = message.pretty_repr(html=True)
    if not indent:
        print(pretty_message, flush=True)
        return

    indented = "\n".join("\t" + c for c in pretty_message.split("\n"))
    print(indented, flush=True)


def pretty_print_update(update, last_message, is_subgraph):
    for node_name, node_update in update.items():
        update_label = f"Update from node {node_name}:"
        if is_subgraph:
            update_label = "\t" + update_label

        print(update_label, flush=True)
        print("\n", flush=True)

        # Check if node_update exists and has messages
        if node_update is None or "messages" not in node_update:
            print(
                (
                    "\t(No messages in this update)"
                    if is_subgraph
                    else "(No messages in this update)"
                ),
                flush=True,
            )

            print("\n", flush=True)
            continue

        # Handle Overwrite objects from LangGraph
        messages_data = node_update["messages"]

        # If it's an Overwrite object, get the value attribute
        if hasattr(messages_data, "value"):
            messages_data = messages_data.value

        # Convert to messages only if we have a list
        if isinstance(messages_data, list):
            messages = convert_to_messages(messages_data)
            if last_message:
                messages = messages[-1:]

            for m in messages:
                pretty_print_message(m, indent=is_subgraph)
        else:
            print(
                (
                    "\t(Unexpected message format)"
                    if is_subgraph
                    else "(Unexpected message format)"
                ),
                flush=True,
            )

        print("\n", flush=True)


def pretty_print_messages(update, last_message=False):
    is_subgraph = False
    if isinstance(update, tuple):
        ns, update = update
        # skip parent graph updates in the printouts
        if len(ns) == 0:
            pretty_print_update(update, last_message, is_subgraph)
            return

        graph_id = ns[-1].split(":")[0]
        print(f"Update from subgraph {graph_id}:", flush=True)
        print("\n", flush=True)
        is_subgraph = True

    pretty_print_update(update, last_message, is_subgraph)
