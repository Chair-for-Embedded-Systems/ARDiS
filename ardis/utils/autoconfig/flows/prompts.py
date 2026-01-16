# Utillity prompts

class SimplePrompts():
    
    @staticmethod
    def single_choice_prompt(
        header_prompt: str,
        choices: list[str],
        max_items_per_page: int,
        max_columns: int
    ) -> str:
        """
        Simple single-choice prompt with pagination and multi-column support.
        Allows the user to select one item from a list of choices.
        """
        current_page = 0
        total_pages = len(choices) // max_items_per_page + (1 if len(choices) == 0 else 0)

        while True:
            print("\033c", end="")
            print(header_prompt)
            # Items on this page
            page_items = choices[current_page * max_items_per_page:min((current_page + 1) * max_items_per_page, len(choices))]

            if total_pages > 1:
                print(f"\n< Page {current_page + 1} of {total_pages} >\n")

            # Print items in a grid if max_columns > 1 the index should be per column
            SimplePrompts.print_item_grid(page_items, max_columns, column_offset=3, enable_index=True)

            # Print page navigation info
            print("\nEnter the index of your choice to select it.")
            if total_pages > 1:
                print("Enter 'n' for next page, 'p' for previous page.")
            input_str = input(f"\n>>> ").strip()

            # Handle navigation
            if input_str.lower() == 'n':
                current_page = (current_page + 1) % total_pages
                continue
            elif input_str.lower() == 'p':
                current_page = (current_page - 1) % total_pages
                continue
            elif input_str.isdigit():
                selection_idx = int(input_str) - 1
                if 0 <= selection_idx < len(page_items):
                    return page_items[selection_idx]
    
    @staticmethod
    def multi_choice_prompt(
        header_prompt: str,
        choices: list[str],
        initial_index_selection: set[int],
        max_items_per_page: int,
        max_columns: int
    ) -> set[str]:
        current_page = 0
        total_pages = len(choices) // max_items_per_page + (1 if len(choices) == 0 else 0)
        
        selected_indices = initial_index_selection.copy()
        while True:
            print("\033c", end="")
            print(header_prompt)
            # Items on this page
            page_items = choices[current_page * max_items_per_page:min((current_page + 1) * max_items_per_page, len(choices))]

            if total_pages > 1:
                print(f"\n< Page {current_page + 1} of {total_pages} >\n")

            # Print items in a grid if max_columns > 1 the index should be per column
            items = []
            for idx, item in enumerate(page_items):
                global_idx = current_page * max_items_per_page + idx
                mark = "[X]" if global_idx in selected_indices else "[ ]"
                item = f"{global_idx + 1:>3}) {mark} {item}"
                items.append(item)

            SimplePrompts.print_item_grid(items, max_columns, column_offset=3, enable_index=False)

            # Print page navigation info
            print(f"\n  [X] = Selected, [ ] = Not Selected")
            print("\nEnter indices separated by spaces to toggle selection.")
            if total_pages > 1:
                print("Enter 'n' for next page, 'p' for previous page.")
            print("Enter 'done' when finished.")
            
            input_str = input(f"\n>>> ").strip()

            # Handle navigation
            if input_str.lower() == 'n':
                current_page = (current_page + 1) % total_pages
                continue
            elif input_str.lower() == 'p':
                current_page = (current_page - 1) % total_pages
                continue
            elif input_str.lower() == 'done':
                break
            else:
                indices = input_str.split()
                for index_str in indices:
                    if index_str.isdigit():
                        index = int(index_str) - 1
                        if 0 <= index < len(choices):
                            if index in selected_indices:
                                selected_indices.remove(index)
                            else:
                                selected_indices.add(index)
        
        return {choices[i] for i in selected_indices}

    @staticmethod
    def print_item_grid(
        items: list[str],
        columns: int,
        column_offset: int = 3,
        padding_left: int = 0,
        enable_index: bool = True
    ) -> None:
        """
        Prints items in an enumerated grid format with specified number of columns.
        """
        if columns > 1:
            rows = (len(items) + columns - 1) // columns
            grid = [[] for _ in range(rows)]

            for idx, item in enumerate(items):
                row_idx = idx % rows
                if enable_index:
                    item_text = f"{idx + 1:>2}) {item}" # Enumerated item and right allign index
                else:
                    item_text = item
                grid[row_idx].append(item_text)

            # Determine longest item per column for formatting
            column_to_max_length = {col: 0 for col in range(columns)}
            for row in grid:
                for col_idx, item in enumerate(row):
                    if len(item) > column_to_max_length[col_idx]:
                        column_to_max_length[col_idx] = len(item)

            for row in grid:
                # Add left padding
                print(" " * padding_left, end="")
                # Print each item with proper spacing
                for col_idx, item in enumerate(row):
                    print(f"{item:<{column_to_max_length[col_idx] + column_offset}}", end="")
                print()
        else:
            for idx, item in enumerate(items):
                print(f"{idx + 1:>{column_offset}}) {item}")

def __test_single_choice_prompt():
    
    test_options = [f"Option {i}" for i in range(1, 101)]
    
    item = SimplePrompts.single_choice_prompt(
        header_prompt="Select an option:",
        choices=test_options,
        max_items_per_page=16,
        max_columns=3,
    )
    print(f"Selected option: {item}")

def __test_multi_choice_prompt():
    
    test_options = [f"Option {i}" for i in range(1, 101)]
    
    items = SimplePrompts.multi_choice_prompt(
        header_prompt="Select multiple options:",
        choices=test_options,
        initial_index_selection=set(),
        max_items_per_page=16,
        max_columns=3,
    )
    print(f"Selected items: {items}")

if __name__ == "__main__":
    __test_single_choice_prompt()
    __test_multi_choice_prompt()