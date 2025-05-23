import ipywidgets as widgets
from IPython.core.magic import Magics, magics_class, line_magic, cell_magic
from IPython.display import display, Markdown, HTML
from IPython import get_ipython
import requests
import json
import shlex # For parsing line magic arguments

# Default URL for the agent backend
AGENT_URL = "http://localhost:8000"
MAX_CONTEXT_HISTORY = 5 # Max number of user/assistant turns to keep in context

class VectorBTProMagics(Magics):
    def __init__(self, shell):
        super(VectorBTProMagics, self).__init__(shell)
        self.agent_url = AGENT_URL
        self.context_history: list[dict[str, str]] = [] # For magic commands
        self.api_key: str | None = None # Stores the API key for the session

    def _add_to_context(self, role: str, content: str):
        """Adds a message to the context history, maintaining a fixed size."""
        if len(self.context_history) >= MAX_CONTEXT_HISTORY * 2: # Each turn has user and assistant
            self.context_history = self.context_history[-(MAX_CONTEXT_HISTORY * 2 - 2):] # Keep n-1 turns
        self.context_history.append({"role": role, "content": content})

    @line_magic
    def vectorbt_init(self, line: str):
        """
        Initializes the VectorBTPro Expert Agent.
        Usage: %vectorbt_init YOUR_GEMINI_API_KEY [optional_docs_path=/path/to/docs]
        """
        args = shlex.split(line)
        if not args:
            print("Usage: %vectorbt_init YOUR_GEMINI_API_KEY [optional_docs_path=/path/to/your/vectorbtpro/docs]")
            print("Please provide your Gemini API key.")
            return

        api_key = args[0]
        self.api_key = api_key # Store for potential future use by the magics if needed

        docs_path = None
        if len(args) > 1:
            # Allow "optional_docs_path=" or just the path for backward compatibility or simplicity
            if args[1].startswith("optional_docs_path="):
                docs_path = args[1].split("=", 1)[1]
            else:
                docs_path = args[1]
        
        payload = {"gemini_api_key": api_key} # Backend primarily uses this key
        if docs_path:
            payload["docs_path"] = docs_path
        
        print(f"Initializing agent at {self.agent_url}/initialize...")
        try:
            response = requests.post(f"{self.agent_url}/initialize", json=payload, timeout=60) # Increased timeout for init
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            result = response.json()
            print(f"Agent initialization: {result.get('status', 'unknown_status')} - {result.get('message', 'No message received.')}")
            if result.get('status') == 'success' or result.get('status') == 'warning':
                print("Agent ready. You can now use %%vectorbt_expert and %vectorbt_status.")
                self.vectorbt_status("") # Show status after successful init
            else:
                print("Initialization might have failed or had issues. Check backend logs for details.")
        except requests.exceptions.RequestException as e:
            print(f"Error initializing agent: {e}")
            print("Please ensure the agent backend is running and accessible at the specified URL.")
        except json.JSONDecodeError:
            print("Error: Could not decode JSON response from the server. The server might have returned an invalid response.")


    @cell_magic
    def vectorbt_expert(self, line: str, cell: str):
        """
        Sends a query to the VectorBTPro Expert Agent.
        Usage:
        %%vectorbt_expert [optional line arguments, currently unused]
        Your query/question for the agent.
        You can include code snippets or ask for explanations.
        """
        query = cell.strip()
        if not query:
            print("Please provide a query in the cell below %%vectorbt_expert.")
            return

        # Check if agent was initialized via %vectorbt_init (checks if self.api_key is set by this magic)
        # This is a soft check; backend handles actual initialization status.
        # if not self.api_key:
        # print("Note: Agent API key not set via %vectorbt_init in this session. Assuming agent is already initialized on the backend.")
        # Allowing queries even if %vectorbt_init wasn't run in this specific notebook session,
        # as the server might be initialized independently. The server will reject if it's not initialized.

        payload = {"query": query, "context": self.context_history}
        
        print("Querying VectorBTPro Expert...")
        try:
            response = requests.post(f"{self.agent_url}/query", json=payload, timeout=180) # Longer timeout for LLM responses
            response.raise_for_status()
            result = response.json()

            agent_response_text = result.get("response", "No response text received.")
            
            self._add_to_context("user", query)
            self._add_to_context("assistant", agent_response_text)

            display(Markdown(agent_response_text))

            code_to_run = result.get("code")
            if code_to_run:
                print("\n--- Suggested Code ---")
                # Display code in a Markdown block for easy copying
                display(Markdown(f"```python\n{code_to_run}\n```"))
                
                confirm = input("Execute the code above? (yes/no): ").strip().lower()
                if confirm == 'yes':
                    print("Executing code...")
                    ipy = get_ipython()
                    if ipy:
                        exec_result = ipy.run_cell(code_to_run, store_history=True)
                        if exec_result.success:
                            print("Code executed successfully.")
                        else:
                            print("Error during code execution:")
                            if exec_result.error_in_exec:
                                # IPython already prints the traceback for run_cell errors.
                                # We can add a custom message if needed.
                                print(f"   Type: {type(exec_result.error_in_exec).__name__}")
                                print(f"   Message: {exec_result.error_in_exec}")
                            else:
                                print("   Unknown error during execution.")
                    else:
                        print("IPython shell not available to execute code.")
                else:
                    print("Code execution cancelled.")
        
        except requests.exceptions.Timeout:
            print("Error: The request to the agent timed out. The agent might be busy or the task is too long.")
        except requests.exceptions.RequestException as e:
            print(f"Error querying agent: {e}")
        except json.JSONDecodeError:
            print("Error: Could not decode JSON response from the server.")

    @line_magic
    def vectorbt_status(self, line: str):
        """Gets the status of the VectorBTPro Expert Agent."""
        print(f"Checking agent status at {self.agent_url}/status...")
        try:
            response = requests.get(f"{self.agent_url}/status", timeout=15)
            response.raise_for_status()
            status_info = response.json()
            print("\n--- Agent Status ---")
            for key, value in status_info.items():
                print(f"{key.replace('_', ' ').title()}: {value}")
            print("--------------------")
        except requests.exceptions.RequestException as e:
            print(f"Error getting agent status: {e}")
        except json.JSONDecodeError:
            print("Error: Could not decode JSON response from the server.")


class VectorBTProWidget:
    def __init__(self, shell):
        self.shell = shell # IPython shell for code execution
        self.agent_url = AGENT_URL
        
        self.chat_history_display = widgets.Output(layout={
            'border': '1px solid #ccc', 
            'height': '350px', 
            'overflow_y': 'auto',
            'padding': '10px'
        })
        
        self.query_input = widgets.Textarea(
            placeholder="Type your question about vectorbtpro here...",
            layout={'width': 'calc(100% - 100px)', 'margin_right': '5px'} # Adjust width for button
        )
        self.submit_button = widgets.Button(description="Send", button_style='success', layout={'width': '90px'})
        
        # UI Assembly
        input_box = widgets.HBox([self.query_input, self.submit_button], layout={'align_items': 'flex-start'})
        self.main_widget = widgets.VBox([self.chat_history_display, input_box])
        
        # Event Handlers
        self.submit_button.on_click(self._on_submit)
        # self.query_input.observe(self._on_text_submit, names='value') # For potential Enter key submission

        self.context_history: list[dict[str, str]] = [] # Independent context for the widget
        self.current_code_to_run: str | None = None 
        self.current_execute_button: widgets.Button | None = None


    def _add_to_widget_context(self, role: str, content: str):
        """Adds a message to the widget's context history."""
        if len(self.context_history) >= MAX_CONTEXT_HISTORY * 2:
            self.context_history = self.context_history[-(MAX_CONTEXT_HISTORY * 2 - 2):]
        self.context_history.append({"role": role, "content": content})

    def _on_submit(self, b=None): 
        query = self.query_input.value.strip()
        if not query:
            return

        with self.chat_history_display:
            display(Markdown(f"<div style='margin-bottom: 5px;'><strong>You:</strong> {query}</div>"))

        self.query_input.value = "" 
        self._process_query(query)
        
    def _execute_code_button_clicked(self, b: widgets.Button):
        """Handles the click of an 'Execute Code' button."""
        # The button itself is passed as 'b'. We retrieve the code associated with this button.
        # This assumes current_code_to_run was set when this button was created.
        code_to_run = self.current_code_to_run
        
        with self.chat_history_display:
            if code_to_run and self.shell:
                display(Markdown("--- Executing Code ---"))
                try:
                    # Disable button during execution
                    if b: b.disabled = True
                    exec_result = self.shell.run_cell(code_to_run, store_history=True)
                    if exec_result.success:
                        display(Markdown("<p style='color:green;'>Code executed successfully.</p>"))
                    else:
                        display(Markdown("<p style='color:red; font-weight:bold;'>Error during code execution:</p>"))
                        # IPython's run_cell usually prints errors, but we can add a summary
                        error_html = f"<pre style='color:red;'>{str(exec_result.error_in_exec or 'Unknown error')}</pre>"
                        display(HTML(error_html))
                except Exception as e:
                    display(Markdown(f"<p style='color:red; font-weight:bold;'>An unexpected error occurred during code execution:</p> <pre style='color:red;'>{e}</pre>"))
                finally:
                    # Re-enable button or change its state if needed
                    if b: b.disabled = False 
            elif not self.shell:
                 display(Markdown("<p style='color:orange;'>IPython shell not available to execute code.</p>"))
            else:
                 display(Markdown("<p style='color:orange;'>No code to execute or code was not stored correctly.</p>"))
            
            # Clear the stored code and button reference after attempting execution
            self.current_code_to_run = None 
            if self.current_execute_button == b: # Only clear if it's the current button
                self.current_execute_button = None


    def _process_query(self, query: str):
        # Clear previous 'Execute Code' button if any, since new query means new context
        if self.current_execute_button:
            # self.current_execute_button.layout.display = 'none' # Hide old button
            self.current_execute_button = None
            self.current_code_to_run = None

        with self.chat_history_display: 
            # Temporary "Processing..." message
            processing_message = widgets.HTML("<em>Processing...</em>")
            display(processing_message)
            
            payload = {"query": query, "context": self.context_history}
            try:
                response = requests.post(f"{self.agent_url}/query", json=payload, timeout=180)
                response.raise_for_status()
                result = response.json()

                agent_response_text = result.get("response", "No response text received.")
                
                self._add_to_widget_context("user", query)
                self._add_to_widget_context("assistant", agent_response_text)
                
                # Remove "Processing..." message by clearing the output it was in (if possible)
                # A bit tricky with widgets.Output. A simpler way is to just let it be overwritten.
                # Or, if we had direct access to the output item, remove it.
                # For now, we'll just display the new content. The "Processing..." will scroll up.

                display(Markdown(f"<div style='margin-top: 10px; margin-bottom:5px;'><strong>Agent:</strong></div>"))
                display(Markdown(agent_response_text)) 

                self.current_code_to_run = result.get("code") 
                if self.current_code_to_run:
                    display(Markdown("--- Suggested Code ---"))
                    display(Markdown(f"```python\n{self.current_code_to_run}\n```"))
                    
                    execute_button = widgets.Button(description="Execute Code", button_style='info', layout={'margin_top': '5px'})
                    execute_button.on_click(self._execute_code_button_clicked)
                    self.current_execute_button = execute_button # Store the new button
                    display(execute_button)

            except requests.exceptions.Timeout:
                 display(Markdown("<p style='color:red;'>Error: The request to the agent timed out.</p>"))
            except requests.exceptions.RequestException as e:
                display(Markdown(f"<p style='color:red;'><strong>Error querying agent:</strong> {e}</p>"))
            except json.JSONDecodeError:
                display(Markdown("<p style='color:red;'><strong>Error: Could not decode JSON response from the server.</strong></p>"))
            except Exception as e:
                display(Markdown(f"<p style='color:red;'><strong>An unexpected error occurred:</strong> {e}</p>"))
            finally:
                # Remove "Processing..." if it's still the last item.
                # This is tricky with widgets.Output. A better way is to update its value.
                # For now, we accept it scrolls up.
                pass


    def show(self): # Renamed from display_widget to avoid IPython.display.display conflict
        """Displays the assembled widget in the Jupyter output."""
        display(self.main_widget)

# Global instance of the widget to be displayed by a helper function
_jupyter_widget_instance = None

def display_vectorbt_expert_widget(): # No shell argument needed if get_ipython() is used inside
    """Creates and displays the chat widget. Uses get_ipython() to get current shell."""
    global _jupyter_widget_instance
    shell = get_ipython()
    if shell is None:
        print("Cannot display widget: Not in an IPython environment.")
        return

    if _jupyter_widget_instance is None:
        _jupyter_widget_instance = VectorBTProWidget(shell)
    
    # Check if agent is initialized (basic check, actual status from backend)
    if _jupyter_widget_instance: # Ensure instance was created
        with _jupyter_widget_instance.chat_history_display:
            _jupyter_widget_instance.chat_history_display.clear_output(wait=True) # Clear previous state
            display(Markdown("Welcome to the VectorBTPro Expert chat!"))
            display(Markdown("Please ensure you have initialized the agent using the `%vectorbt_init` magic command if this is the first time or if the backend restarted."))
            display(Markdown("Example: `%vectorbt_init YOUR_GEMINI_API_KEY`"))
            display(Markdown("You can check the agent's status with `%vectorbt_status`."))
        _jupyter_widget_instance.show()


def display_welcome_instructions():
    """Displays a welcome message and basic instructions when the extension loads."""
    welcome_html = """
    <div style="padding: 15px; border: 1px solid #ccc; border-radius: 5px; background-color: #f9f9f9; font-family: sans-serif;">
        <h2>VectorBTPro Expert Agent Extension Loaded!</h2>
        <p>This extension provides magic commands and a chat widget to interact with the VectorBTPro AI Agent.</p>
        
        <h3><span style="color: #007bff;">Step 1: Initialization</span></h3>
        <p>Before using the agent, you <strong>must</strong> initialize it with your Gemini API Key. Run this in a cell:</p>
        <pre style="background-color: #eef; padding: 10px; border-radius: 3px;"><code>%vectorbt_init YOUR_GEMINI_API_KEY [optional_docs_path=/path/to/docs]</code></pre>
        <p>Example: <code>%vectorbt_init mysecretapikey</code></p>
        <p>The <code>optional_docs_path</code> is the path <em>within the Docker container</em> where <code>vectorbtpro/docs</code> are located. The default is <code>/home/jovyan/vectorbtpro/docs</code>.</p>

        <h3><span style="color: #007bff;">Step 2: Usage</span></h3>
        <h4>Magic Commands:</h4>
        <ul style="list-style-type: disc; margin-left: 20px;">
            <li><strong>Check Status:</strong> <code>%vectorbt_status</code></li>
            <li><strong>Ask a Question (Cell Magic):</strong>
                <pre style="background-color: #eef; padding: 10px; border-radius: 3px;"><code>%%vectorbt_expert
Your question about vectorbtpro, e.g., "How to calculate RSI?"</code></pre>
            </li>
        </ul>

        <h4>Interactive Chat Widget:</h4>
        <p>For a chat-like experience, load the widget by running this in a cell:</p>
        <pre style="background-color: #eef; padding: 10px; border-radius: 3px;"><code>from agent_system.jupyter_extension import display_vectorbt_expert_widget
display_vectorbt_expert_widget()</code></pre>
        <p>The widget allows you to chat with the agent and execute suggested code snippets directly within its interface.</p>
        
        <p style="margin-top:15px; font-weight:bold;">Note:</p>
        <ul style="list-style-type: disc; margin-left: 20px;">
            <li>Ensure the agent backend server is running (this is usually handled by <code>start.sh</code> in the Docker container).</li>
            <li>The context (conversation memory) is managed separately for magic commands and the chat widget.</li>
        </ul>
    </div>
    """
    display(HTML(welcome_html))

def load_ipython_extension(ipython):
    """
    This function is called when the extension is loaded.
    It registers the magic class and displays a welcome message.
    """
    global _jupyter_widget_instance # Ensure we can clear it on unload
    _jupyter_widget_instance = None # Reset widget instance on load/reload

    ipython.register_magics(VectorBTProMagics)
    
    # Defer welcome message to avoid issues during startup/import checks by some environments
    ipython.kernel.shell_handlers["execute_request"].add_pre_execute_hook(
        lambda: display_welcome_instructions_once(ipython)
    )
    print("VectorBTPro Expert Agent extension loaded. Run a cell to see instructions or use `display_welcome_instructions()`.")


_welcome_message_displayed = False
def display_welcome_instructions_once(ipython):
    global _welcome_message_displayed
    if not _welcome_message_displayed:
        display_welcome_instructions()
        _welcome_message_displayed = True
    # Remove the hook after first execution
    if ipython and ipython.kernel:
         try:
            ipython.kernel.shell_handlers["execute_request"].remove_pre_execute_hook(
                lambda: display_welcome_instructions_once(ipython)
            )
         except ValueError: # Hook might already be removed if reloaded multiple times
            pass


def unload_ipython_extension(ipython):
    """
    This function is called when the extension is unloaded.
    It can be used to clean up any resources.
    """
    global _jupyter_widget_instance, _welcome_message_displayed
    _jupyter_widget_instance = None 
    _welcome_message_displayed = False # Reset for next load
    # Magics are unregistered automatically by IPython when the module is reloaded or unloaded.
    print("VectorBTPro Expert Agent extension unloaded.")

# Make the function available for users if they miss the initial display
def show_welcome():
    display_welcome_instructions()

# Example of how to manually load in a notebook:
# %load_ext agent_system.jupyter_extension

# Example of how to display the widget:
# from agent_system.jupyter_extension import display_vectorbt_expert_widget
# display_vectorbt_expert_widget()
```
