from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich import box
import time

console = Console()

def show_welcome():
    console.print(Panel.fit(
        "[bold cyan]CCDI Scraper[/bold cyan]\n"
        "[dim]Central Commission for Discipline Inspection Data Acquisition System[/dim]\n\n"
        "Initializing system components...",
        box=box.ROUNDED,
        style="blue"
    ))

def show_status_table(checks):
    """
    Show a table of health checks.
    checks: list of (Name, Status, Msg) tuples.
    Status: "ok" (green), "warn" (yellow), "error" (red)
    """
    table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
    table.add_column("Component")
    table.add_column("Status")
    table.add_column("Message")
    
    for name, status, msg in checks:
        if status == "ok":
            status_str = "[green]OK[/green]"
        elif status == "warn":
            status_str = "[yellow]WARN[/yellow]"
        else:
            status_str = "[red]FAIL[/red]"
        table.add_row(name, status_str, msg)
        
    console.print(table)
    console.print()

def create_progress():
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    )

def log_message(full_text, level="info"):
    if level == "info":
        console.print(f"[blue][INFO][/blue] {full_text}")
    elif level == "success":
        console.print(f"[green][SUCCESS][/green] {full_text}")
    elif level == "warning":
        console.print(f"[yellow][WARN][/yellow] {full_text}")
    elif level == "error":
        console.print(f"[red][ERROR][/red] {full_text}")
