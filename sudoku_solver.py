import wx
import threading
import time
import random
from typing import List, Tuple, Optional

# ============================================================================
# PUZZLE BANK (Categorized by Difficulty) - VERIFIED VALID PUZZLES
# ============================================================================

RAW_PUZZLE_BANK = {
    'Easy': [
        '53..7....6..195....98....6.8...6...34..8.3..17...2...6.6....28....419..5....8..79',
        '..3.2.6..9..3.5..1..18.64....81.29..7.......8..67.82....26.95..8..2.3..9..5.1.3..',
        '2...8.3...6..7..84.3.5..2.9...1.54.8.........4.27.6...3.1..7.4.72..4..6...4.1...3',
    ],
    'Medium': [
        '1....7.9..3..2...8..96..5....53..9...1..8...26....4...3......1..4......7..7...3..',
        '6.....8.3.4.7.................5.4.7.3......2.....5.....9..1....8.......2.9.7.....5',
    ],
    'Hard': [
        '8..........36......7..9.2...5...7.......457.....1...3...1....68..85...1..9....4..',
        '....7..5...21..9..1...28....7...5..1..851.....5....3.......3..68........21.....87',
    ]
}

def sanitize_puzzle_bank(raw_dict):
    """Sanitize and validate puzzle bank dictionary"""
    PUZZLE_BANK = []
    for difficulty, puzzles in raw_dict.items():
        for puzzle in puzzles:
            # Basic length check
            if len(puzzle) != 81:
                continue
            # Character check
            if not all(c in '0123456789.' for c in puzzle):
                continue
            # Try to validate the puzzle
            try:
                test_solver = FastSudokuSolver()
                test_solver.load_board(puzzle)
                # If it loads without error, add it
                PUZZLE_BANK.append((difficulty, puzzle))
            except:
                # Skip invalid puzzles
                continue
    
    return PUZZLE_BANK if PUZZLE_BANK else [("Easy", "." * 81)]

# ============================================================================
# FAST SUDOKU SOLVER (Backtracking + MRV + Bitmasks)
# ============================================================================

class FastSudokuSolver:
    """Efficient Sudoku solver using backtracking with MRV heuristic"""
    
    def __init__(self):
        self.board = [[0]*9 for _ in range(9)]
        self.row_masks = [0]*9
        self.col_masks = [0]*9
        self.box_masks = [0]*9
        self.stop_requested = False

    def load_board(self, puzzle: str):
        """Load puzzle string into board"""
        if not isinstance(puzzle, str) or len(puzzle) != 81:
            raise ValueError("Puzzle must be 81-character string")
        
        # Reset board
        self.board = [[0]*9 for _ in range(9)]
        self.row_masks = [0]*9
        self.col_masks = [0]*9
        self.box_masks = [0]*9
        
        for i in range(9):
            for j in range(9):
                ch = puzzle[i*9 + j]
                if ch.isdigit() and ch != '0':
                    v = int(ch)
                    if not (1 <= v <= 9):
                        raise ValueError(f"Digits must be 1-9, found {v}")
                    
                    bit = 1 << (v-1)
                    bidx = (i//3)*3 + (j//3)
                    
                    # Check for conflicts
                    if self.row_masks[i] & bit:
                        raise ValueError(f"Duplicate {v} in row {i}")
                    if self.col_masks[j] & bit:
                        raise ValueError(f"Duplicate {v} in column {j}")
                    if self.box_masks[bidx] & bit:
                        raise ValueError(f"Duplicate {v} in box {bidx}")
                    
                    self.board[i][j] = v
                    self.row_masks[i] |= bit
                    self.col_masks[j] |= bit
                    self.box_masks[bidx] |= bit
                elif ch not in '.0':
                    raise ValueError(f"Invalid character: {ch}")

    def _get_candidates(self, r, c):
        """Get valid candidates for cell using bitmasks"""
        if self.board[r][c] != 0:
            return []
        bidx = (r//3)*3 + (c//3)
        used = self.row_masks[r] | self.col_masks[c] | self.box_masks[bidx]
        return [v for v in range(1,10) if not (used & (1 << (v-1)))]

    def _find_mrv_cell(self):
        """Find cell with minimum remaining values"""
        best = None
        best_len = 10
        for i in range(9):
            for j in range(9):
                if self.board[i][j] == 0:
                    cands = self._get_candidates(i,j)
                    if not cands:
                        return None
                    if len(cands) < best_len:
                        best_len = len(cands)
                        best = (i,j,cands)
                        if best_len == 1:
                            return best
        return best

    def solve(self) -> bool:
        """Solve the puzzle"""
        self.stop_requested = False
        return self._solve_recursive()

    def _solve_recursive(self):
        """Recursive backtracking solver"""
        if self.stop_requested:
            return False
        
        cell = self._find_mrv_cell()
        if cell is None:
            # Check if solved
            for r in range(9):
                for c in range(9):
                    if self.board[r][c] == 0:
                        return False
            return True
        
        r, c, cands = cell
        for v in cands:
            if self.stop_requested:
                return False
            
            bit = 1 << (v-1)
            bidx = (r//3)*3 + (c//3)
            self.board[r][c] = v
            self.row_masks[r] |= bit
            self.col_masks[c] |= bit
            self.box_masks[bidx] |= bit
            
            if self._solve_recursive():
                return True
            
            # Backtrack
            self.board[r][c] = 0
            self.row_masks[r] &= ~bit
            self.col_masks[c] &= ~bit
            self.box_masks[bidx] &= ~bit
        
        return False

    def get_solution(self):
        """Get solved board"""
        return [row[:] for row in self.board]

    def stop(self):
        """Stop solving"""
        self.stop_requested = True

# Initialize puzzle bank AFTER defining FastSudokuSolver
PUZZLE_BANK = sanitize_puzzle_bank(RAW_PUZZLE_BANK)

# ============================================================================
# MODE SELECTOR DIALOG
# ============================================================================

class ModeSelector(wx.Dialog):
    """Colorful mode selection dialog"""
    
    def __init__(self, parent):
        super().__init__(parent, title="Sudoku - Select Mode", size=(450, 380))
        self.mode = None
        self._init_ui()
        self.CenterOnScreen()

    def _init_ui(self):
        panel = wx.Panel(self)
        panel.SetBackgroundColour(wx.Colour(245, 240, 250))
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title with gradient effect
        title = wx.StaticText(panel, label="🎮 Sudoku Master 🎮")
        title.SetFont(wx.Font(24, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        title.SetForegroundColour(wx.Colour(88, 86, 214))
        main_sizer.Add(title, 0, wx.CENTER|wx.ALL, 20)
        
        subtitle = wx.StaticText(panel, label="Choose Your Mode")
        subtitle.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL))
        subtitle.SetForegroundColour(wx.Colour(120, 115, 180))
        main_sizer.Add(subtitle, 0, wx.CENTER|wx.BOTTOM, 20)
        
        # Solver Mode Button - Purple
        solver_btn = wx.Button(panel, label="🔧 SOLVER MODE", size=(300, 60))
        solver_btn.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        solver_btn.SetBackgroundColour(wx.Colour(108, 99, 255))
        solver_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        solver_btn.Bind(wx.EVT_BUTTON, lambda e: self._select_mode("solver"))
        main_sizer.Add(solver_btn, 0, wx.CENTER|wx.ALL, 10)
        
        solver_desc = wx.StaticText(panel, label="Input any puzzle and let AI solve it")
        solver_desc.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL))
        solver_desc.SetForegroundColour(wx.Colour(120, 120, 140))
        main_sizer.Add(solver_desc, 0, wx.CENTER|wx.BOTTOM, 15)
        
        # Play Mode Button - Teal
        play_btn = wx.Button(panel, label="🎯 PLAY MODE", size=(300, 60))
        play_btn.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        play_btn.SetBackgroundColour(wx.Colour(32, 178, 170))
        play_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        play_btn.Bind(wx.EVT_BUTTON, lambda e: self._select_mode("play"))
        main_sizer.Add(play_btn, 0, wx.CENTER|wx.ALL, 10)
        
        play_desc = wx.StaticText(panel, label="Challenge yourself with puzzles")
        play_desc.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_ITALIC, wx.FONTWEIGHT_NORMAL))
        play_desc.SetForegroundColour(wx.Colour(120, 120, 140))
        main_sizer.Add(play_desc, 0, wx.CENTER)
        
        panel.SetSizer(main_sizer)

    def _select_mode(self, mode):
        """Select mode and close dialog"""
        self.mode = mode
        self.EndModal(wx.ID_OK)

# ============================================================================
# MAIN SUDOKU FRAME
# ============================================================================

class SudokuFrame(wx.Frame):
    """Main application frame"""
    
    def __init__(self):
        # Dynamic sizing
        disp_w, disp_h = wx.GetDisplaySize()
        init_w = min(950, max(700, disp_w - 100))
        init_h = min(950, max(700, disp_h - 150))
        
        super().__init__(None, title="Sudoku Master", size=(init_w, init_h))
        self.SetMaxSize((disp_w, disp_h))
        
        # State variables
        self.cells = [[None]*9 for _ in range(9)]
        self.clues = [[False]*9 for _ in range(9)]
        self.hinted = [[False]*9 for _ in range(9)]
        self.solver = FastSudokuSolver()
        self.solving = False
        self.solution = None
        self.current_puzzle_idx = 0
        self.hints_remaining = 3
        self.max_hints = 3
        self.undo_stack = []
        self.redo_stack = []
        self.timer_running = False
        self.start_time = 0.0
        self.elapsed_time = 0
        self.timer = None
        self.timer_enabled = False
        self.animate = True
        self.anim_delay = 10
        self.loading_puzzle = False
        
        # Color schemes - Purple & Teal palette
        self.play_bg = wx.Colour(240, 250, 248)
        self.solver_bg = wx.Colour(245, 243, 255)
        self.box_colors_play = [
            wx.Colour(224, 242, 241),
            wx.Colour(248, 252, 252),
        ]
        self.box_colors_solver = [
            wx.Colour(238, 233, 255),
            wx.Colour(248, 248, 255),
        ]
        
        self._init_ui()
        self._show_mode_selector()
        
        self.Bind(wx.EVT_CLOSE, self._on_close)
        self.Bind(wx.EVT_SIZE, self._on_resize)

    def _get_box_index(self, r, c):
        """Get 3x3 box index"""
        return (r//3)*3 + (c//3)

    def _set_cell_color(self, r, c, highlight=None):
        """Set cell background color"""
        try:
            if highlight:
                self.cells[r][c].SetBackgroundColour(highlight)
            else:
                box_idx = self._get_box_index(r, c)
                colors = self.box_colors_play if self.mode == "play" else self.box_colors_solver
                color_idx = (box_idx // 3 + box_idx % 3) % 2
                self.cells[r][c].SetBackgroundColour(colors[color_idx])
            self.cells[r][c].Refresh()
        except:
            pass

    def _temp_highlight(self, r, c, color, delay_ms=400):
        """Temporarily highlight a cell"""
        try:
            self._set_cell_color(r, c, color)
            wx.CallLater(delay_ms, lambda: self._set_cell_color(r, c))
        except:
            pass

    def _init_ui(self):
        """Initialize user interface"""
        self.panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        self._init_top_bar(self.panel, main_sizer)
        self._init_grid(self.panel, main_sizer)
        self._init_solver_controls(self.panel, main_sizer)
        self._init_play_controls(self.panel, main_sizer)
        
        self.panel.SetSizer(main_sizer)
        self.Centre()

    def _init_top_bar(self, parent, sizer):
        """Initialize top bar with back button and mode label"""
        top_panel = wx.Panel(parent)
        top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.back_btn = wx.Button(top_panel, label="← Back to Menu", size=(120, 32))
        self.back_btn.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        self.back_btn.Bind(wx.EVT_BUTTON, self._on_back)
        top_sizer.Add(self.back_btn, 0, wx.ALL, 8)
        
        top_sizer.AddStretchSpacer()
        
        self.mode_label = wx.StaticText(top_panel, label="")
        self.mode_label.SetFont(wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        top_sizer.Add(self.mode_label, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 8)
        
        top_sizer.AddStretchSpacer()
        top_sizer.Add((120, 32), 0, wx.ALL, 8)
        
        top_panel.SetSizer(top_sizer)
        sizer.Add(top_panel, 0, wx.EXPAND)

    def _init_grid(self, parent, sizer):
        """Initialize Sudoku grid"""
        grid_panel = wx.Panel(parent)
        grid_sizer = wx.GridSizer(9, 9, 2, 2)
        
        font = wx.Font(18, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        
        for i in range(9):
            for j in range(9):
                cell = wx.TextCtrl(grid_panel, style=wx.TE_CENTER|wx.BORDER_SIMPLE)
                cell.SetMaxLength(1)
                cell.SetFont(font)
                cell.SetMinSize((60, 60))
                cell.SetForegroundColour(wx.Colour(0, 0, 0))
                cell.Bind(wx.EVT_CHAR, lambda e, r=i, c=j: self._on_char(e, r, c))
                cell.Bind(wx.EVT_TEXT, lambda e, r=i, c=j: self._on_text(e, r, c))
                self.cells[i][j] = cell
                grid_sizer.Add(cell, 0, wx.EXPAND)
        
        grid_panel.SetSizer(grid_sizer)
        sizer.Add(grid_panel, 2, wx.EXPAND|wx.ALL, 15)

    def _init_solver_controls(self, parent, sizer):
        """Initialize solver mode controls"""
        self.solver_panel = wx.Panel(parent)
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.solve_btn = wx.Button(self.solver_panel, label="⚡ SOLVE PUZZLE", size=(-1, 45))
        self.solve_btn.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.solve_btn.SetBackgroundColour(wx.Colour(108, 99, 255))
        self.solve_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.solve_btn.Bind(wx.EVT_BUTTON, self._on_solve)
        btn_sizer.Add(self.solve_btn, 2, wx.ALL|wx.EXPAND, 5)
        
        self.clear_btn = wx.Button(self.solver_panel, label="🗑️ CLEAR", size=(-1, 45))
        self.clear_btn.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.clear_btn.SetBackgroundColour(wx.Colour(148, 139, 255))
        self.clear_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.clear_btn.Bind(wx.EVT_BUTTON, self._on_clear)
        btn_sizer.Add(self.clear_btn, 1, wx.ALL|wx.EXPAND, 5)
        
        panel_sizer.Add(btn_sizer, 0, wx.EXPAND)
        
        anim_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.anim_check = wx.CheckBox(self.solver_panel, label="✨ Animation")
        self.anim_check.SetValue(True)
        self.anim_check.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.anim_check.Bind(wx.EVT_CHECKBOX, self._on_anim_toggle)
        anim_sizer.Add(self.anim_check, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 8)
        
        anim_sizer.Add(wx.StaticText(self.solver_panel, label="Speed:"), 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 8)
        
        self.speed_slider = wx.Slider(self.solver_panel, value=10, minValue=0, maxValue=50, style=wx.SL_HORIZONTAL)
        self.speed_slider.Bind(wx.EVT_SLIDER, self._on_speed_change)
        anim_sizer.Add(self.speed_slider, 1, wx.ALL|wx.EXPAND, 5)
        
        panel_sizer.Add(anim_sizer, 0, wx.EXPAND|wx.ALL, 5)
        
        self.solver_panel.SetSizer(panel_sizer)
        sizer.Add(self.solver_panel, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        self.solver_panel.Hide()

    def _init_play_controls(self, parent, sizer):
        """Initialize play mode controls"""
        self.play_panel = wx.Panel(parent)
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        
        info_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.difficulty_label = wx.StaticText(self.play_panel, label="Difficulty: Easy")
        self.difficulty_label.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.difficulty_label.SetForegroundColour(wx.Colour(32, 178, 170))
        info_sizer.Add(self.difficulty_label, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        
        info_sizer.AddStretchSpacer()
        
        self.timer_check = wx.CheckBox(self.play_panel, label="⏱️ Timer")
        self.timer_check.SetValue(False)
        self.timer_check.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.timer_check.Bind(wx.EVT_CHECKBOX, self._on_timer_toggle)
        info_sizer.Add(self.timer_check, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        
        info_sizer.Add((10, 0), 0)
        
        self.timer_label = wx.StaticText(self.play_panel, label="00:00", style=wx.ST_NO_AUTORESIZE)
        self.timer_label.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.timer_label.SetForegroundColour(wx.Colour(20, 150, 140))
        info_sizer.Add(self.timer_label, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        
        self.cells_label = wx.StaticText(self.play_panel, label="📝 Remaining: 0")
        self.cells_label.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        info_sizer.Add(self.cells_label, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 5)
        
        panel_sizer.Add(info_sizer, 0, wx.EXPAND|wx.ALL, 5)
        
        nav_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.prev_btn = wx.Button(self.play_panel, label="◄ Prev", size=(-1, 28))
        self.prev_btn.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        self.prev_btn.SetBackgroundColour(wx.Colour(72, 209, 204))
        self.prev_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.prev_btn.Bind(wx.EVT_BUTTON, self._on_prev_puzzle)
        nav_sizer.Add(self.prev_btn, 1, wx.ALL, 3)
        
        self.random_btn = wx.Button(self.play_panel, label="🎲 Random", size=(-1, 28))
        self.random_btn.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        self.random_btn.SetBackgroundColour(wx.Colour(48, 196, 188))
        self.random_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.random_btn.Bind(wx.EVT_BUTTON, self._on_random_puzzle)
        nav_sizer.Add(self.random_btn, 1, wx.ALL, 3)
        
        self.next_btn = wx.Button(self.play_panel, label="Next ►", size=(-1, 28))
        self.next_btn.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        self.next_btn.SetBackgroundColour(wx.Colour(72, 209, 204))
        self.next_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.next_btn.Bind(wx.EVT_BUTTON, self._on_next_puzzle)
        nav_sizer.Add(self.next_btn, 1, wx.ALL, 3)
        
        self.import_btn = wx.Button(self.play_panel, label="📥 Import", size=(-1, 28))
        self.import_btn.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        self.import_btn.SetBackgroundColour(wx.Colour(64, 224, 208))
        self.import_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.import_btn.Bind(wx.EVT_BUTTON, self._on_import_puzzle)
        nav_sizer.Add(self.import_btn, 1, wx.ALL, 3)
        
        panel_sizer.Add(nav_sizer, 0, wx.EXPAND)
        
        action_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.hint_btn = wx.Button(self.play_panel, label="💡 HINT", size=(-1, 32))
        self.hint_btn.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.hint_btn.SetBackgroundColour(wx.Colour(48, 196, 188))
        self.hint_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.hint_btn.Bind(wx.EVT_BUTTON, self._on_hint)
        action_sizer.Add(self.hint_btn, 2, wx.ALL, 3)
        
        self.hints_label = wx.StaticText(self.play_panel, label=f"({self.hints_remaining}/3)")
        self.hints_label.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        action_sizer.Add(self.hints_label, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 3)
        
        self.undo_btn = wx.Button(self.play_panel, label="↶ Undo", size=(-1, 32))
        self.undo_btn.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        self.undo_btn.SetBackgroundColour(wx.Colour(48, 196, 188))
        self.undo_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.undo_btn.Bind(wx.EVT_BUTTON, self._on_undo)
        action_sizer.Add(self.undo_btn, 1, wx.ALL, 3)
        
        self.redo_btn = wx.Button(self.play_panel, label="↷ Redo", size=(-1, 32))
        self.redo_btn.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        self.redo_btn.SetBackgroundColour(wx.Colour(48, 196, 188))
        self.redo_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.redo_btn.Bind(wx.EVT_BUTTON, self._on_redo)
        action_sizer.Add(self.redo_btn, 1, wx.ALL, 3)
        
        panel_sizer.Add(action_sizer, 0, wx.EXPAND)
        
        self.solve_play_btn = wx.Button(self.play_panel, label="⚡ SOLVE", size=(-1, 40))
        self.solve_play_btn.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.solve_play_btn.SetBackgroundColour(wx.Colour(32, 178, 170))
        self.solve_play_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.solve_play_btn.Bind(wx.EVT_BUTTON, self._on_solve_play)
        panel_sizer.Add(self.solve_play_btn, 0, wx.EXPAND|wx.ALL, 5)
        
        self.play_panel.SetSizer(panel_sizer)
        sizer.Add(self.play_panel, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        self.play_panel.Hide()

    # ========================================================================
    # MODE MANAGEMENT
    # ========================================================================

    def _show_mode_selector(self):
        """Show mode selection dialog"""
        dlg = ModeSelector(self)
        try:
            if dlg.ShowModal() == wx.ID_OK:
                self.mode = dlg.mode
                self._setup_mode()
            else:
                self.Close()
        finally:
            dlg.Destroy()

    def _setup_mode(self):
        """Setup UI for selected mode"""
        if self.mode == "solver":
            self.mode_label.SetLabel("🔧 SOLVER MODE")
            self.mode_label.SetForegroundColour(wx.Colour(108, 99, 255))
            self.panel.SetBackgroundColour(self.solver_bg)
            self.solver_panel.SetBackgroundColour(self.solver_bg)
            self.play_panel.Hide()
            self.solver_panel.Show()
            self._clear_board()
        else:
            self.mode_label.SetLabel("🎯 PLAY MODE")
            self.mode_label.SetForegroundColour(wx.Colour(32, 178, 170))
            self.panel.SetBackgroundColour(self.play_bg)
            self.play_panel.SetBackgroundColour(self.play_bg)
            self.solver_panel.Hide()
            self.play_panel.Show()
            try:
                self._load_puzzle(self.current_puzzle_idx)
            except Exception as e:
                wx.MessageBox(f"Could not load puzzle: {e}", "Error", wx.OK|wx.ICON_ERROR)
        
        for i in range(9):
            for j in range(9):
                self._set_cell_color(i, j)
        
        self.panel.Layout()
        self.Layout()

    def _on_back(self, event):
        """Return to mode selector"""
        self._stop_timer()
        if self.solving:
            self.solver.stop()
        self._show_mode_selector()

    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================

    def _on_char(self, event, row, col):
        """Handle character input"""
        try:
            key = event.GetKeyCode()
            
            if key == wx.WXK_UP and row > 0:
                self.cells[row-1][col].SetFocus()
                return
            if key == wx.WXK_DOWN and row < 8:
                self.cells[row+1][col].SetFocus()
                return
            if key == wx.WXK_LEFT and col > 0:
                self.cells[row][col-1].SetFocus()
                return
            if key == wx.WXK_RIGHT and col < 8:
                self.cells[row][col+1].SetFocus()
                return
            
            if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
                if row < 8:
                    self.cells[row+1][col].SetFocus()
                return
            
            if key == wx.WXK_BACK:
                if not self.clues[row][col]:
                    self.cells[row][col].SetValue("")
                return
            
            if event.ControlDown():
                if key in (ord('Z'), ord('z')):
                    self._on_undo(None)
                    return
                if key in (ord('Y'), ord('y')):
                    self._on_redo(None)
                    return
            
            if ord('1') <= key <= ord('9') or key in (wx.WXK_TAB, wx.WXK_DELETE):
                event.Skip()
            else:
                return
        except:
            event.Skip()

    def _on_text(self, event, row, col):
        """Handle text change"""
        try:
            if self.clues[row][col]:
                return
            
            value = self.cells[row][col].GetValue()
            
            if self.mode == "play" and value:
                self.undo_stack.append((row, col, "", value))
                self.redo_stack.clear()
                if len(self.undo_stack) > 300:
                    self.undo_stack.pop(0)
            
            if self.mode == "play" and value and col < 8:
                self.cells[row][col+1].SetFocus()
            
            if value and (not value.isdigit() or value == '0'):
                self.cells[row][col].SetValue("")
                self._temp_highlight(row, col, wx.Colour(220, 200, 255), 450)
                if self.mode == "solver":
                    wx.MessageBox(
                        "Invalid input! Only digits 1-9 are allowed.",
                        "Invalid Input",
                        wx.OK | wx.ICON_WARNING
                    )
                return
            
            if value:
                self._validate_cell(row, col)
            else:
                self._set_cell_color(row, col)
            
            if self.mode == "play":
                self._update_cells_remaining()
        except:
            pass

    def _validate_cell(self, row, col):
        """Validate cell value against Sudoku rules"""
        try:
            value = self.cells[row][col].GetValue()
            if not value:
                self._set_cell_color(row, col)
                return
            
            for c in range(9):
                if c != col and self.cells[row][c].GetValue() == value:
                    self._temp_highlight(row, col, wx.Colour(255, 200, 200), 600)
                    if self.mode == "solver":
                        wx.MessageBox(
                            f"❌ Sudoku Rule Violation!\n\n"
                            f"Number '{value}' already exists in Row {row + 1}.\n\n"
                            f"Each row must contain unique digits 1-9.",
                            "Invalid Placement",
                            wx.OK | wx.ICON_ERROR
                        )
                        wx.CallAfter(lambda: self.cells[row][col].SetValue(""))
                    return
            
            for r in range(9):
                if r != row and self.cells[r][col].GetValue() == value:
                    self._temp_highlight(row, col, wx.Colour(255, 200, 200), 600)
                    if self.mode == "solver":
                        wx.MessageBox(
                            f"❌ Sudoku Rule Violation!\n\n"
                            f"Number '{value}' already exists in Column {col + 1}.\n\n"
                            f"Each column must contain unique digits 1-9.",
                            "Invalid Placement",
                            wx.OK | wx.ICON_ERROR
                        )
                        wx.CallAfter(lambda: self.cells[row][col].SetValue(""))
                    return
            
            box_row, box_col = (row // 3) * 3, (col // 3) * 3
            for r in range(box_row, box_row + 3):
                for c in range(box_col, box_col + 3):
                    if (r, c) != (row, col) and self.cells[r][c].GetValue() == value:
                        self._temp_highlight(row, col, wx.Colour(255, 200, 200), 600)
                        if self.mode == "solver":
                            box_num = (row // 3) * 3 + (col // 3) + 1
                            wx.MessageBox(
                                f"❌ Sudoku Rule Violation!\n\n"
                                f"Number '{value}' already exists in 3×3 Box #{box_num}.\n\n"
                                f"Each 3×3 box must contain unique digits 1-9.",
                                "Invalid Placement",
                                wx.OK | wx.ICON_ERROR
                            )
                            wx.CallAfter(lambda: self.cells[row][col].SetValue(""))
                        return
            
            self._temp_highlight(row, col, wx.Colour(200, 255, 240), 200)
        except:
            pass

    # ========================================================================
    # SOLVER MODE FUNCTIONS
    # ========================================================================

    def _on_solve(self, event):
        """Solve the puzzle"""
        if self.solving:
            return
        
        puzzle = ""
        try:
            for i in range(9):
                for j in range(9):
                    value = self.cells[i][j].GetValue()
                    if value and (not value.isdigit() or value == '0'):
                        raise ValueError("Invalid digit")
                    puzzle += value if value else "."
                    if value:
                        self.clues[i][j] = True
        except Exception as e:
            wx.MessageBox(f"Invalid board input: {e}", "Error", wx.OK|wx.ICON_ERROR)
            return
        
        self.solving = True
        self.solve_btn.SetLabel("⚡ SOLVING...")
        self.solve_btn.Enable(False)
        
        thread = threading.Thread(target=self._solve_worker, args=(puzzle,), daemon=True)
        thread.start()

    def _solve_worker(self, puzzle):
        """Worker thread for solving"""
        try:
            self.solver.load_board(puzzle)
        except Exception as e:
            wx.CallAfter(lambda: wx.MessageBox(f"Invalid puzzle: {e}", "Error", wx.OK|wx.ICON_ERROR))
            wx.CallAfter(self._solve_complete)
            return
        
        try:
            if self.solver.solve():
                self.solution = self.solver.get_solution()
                wx.CallAfter(self._apply_solution_visual)
            else:
                wx.CallAfter(lambda: wx.MessageBox("No solution found! Check clues.", "Error", wx.OK|wx.ICON_ERROR))
        except Exception as e:
            wx.CallAfter(lambda: wx.MessageBox(f"Solver error: {e}", "Error", wx.OK|wx.ICON_ERROR))
        finally:
            wx.CallAfter(self._solve_complete)

    def _apply_solution_visual(self):
        """Apply solution with optional animation"""
        if not self.solution:
            return
        
        cells_to_fill = [(i, j) for i in range(9) for j in range(9) if not self.clues[i][j]]
        
        if not self.animate or self.anim_delay == 0:
            for i, j in cells_to_fill:
                self.cells[i][j].SetValue(str(self.solution[i][j]))
                self._set_cell_color(i, j)
        else:
            self._animate_cells(cells_to_fill, 0)

    def _animate_cells(self, cells, idx):
        """Animate filling cells"""
        if idx >= len(cells):
            return
        
        i, j = cells[idx]
        try:
            self._set_cell_color(i, j, wx.Colour(230, 230, 255))
            self.cells[i][j].SetValue(str(self.solution[i][j]))
            wx.CallLater(self.anim_delay, lambda: (
                self._set_cell_color(i, j),
                wx.CallLater(self.anim_delay, self._animate_cells, cells, idx + 1)
            ))
        except:
            pass

    def _solve_complete(self):
        """Clean up after solving"""
        self.solving = False
        self.solve_btn.SetLabel("⚡ SOLVE PUZZLE")
        try:
            self.solve_btn.Enable(True)
        except:
            pass

    def _on_clear(self, event):
        """Clear the board"""
        if self.solving:
            self.solver.stop()
        self._clear_board()

    def _on_anim_toggle(self, event):
        """Toggle animation"""
        self.animate = self.anim_check.GetValue()

    def _on_speed_change(self, event):
        """Change animation speed"""
        self.anim_delay = self.speed_slider.GetValue()

    def _on_timer_toggle(self, event):
        """Toggle timer on/off"""
        self.timer_enabled = self.timer_check.GetValue()
        if self.timer_enabled:
            self._start_timer()
        else:
            self._stop_timer()
            self.timer_label.SetLabel("00:00")

    # ========================================================================
    # PLAY MODE FUNCTIONS
    # ========================================================================

    def _load_puzzle(self, idx: int):
        """Load a puzzle from the bank"""
        if self.loading_puzzle:
            return
        
        self.loading_puzzle = True
        
        try:
            if not isinstance(idx, int) or not (0 <= idx < len(PUZZLE_BANK)):
                raise IndexError("Puzzle index out of range")
            
            difficulty, puzzle = PUZZLE_BANK[idx]
            if not isinstance(puzzle, str) or len(puzzle) != 81:
                raise ValueError("Invalid puzzle length")
            
            self.current_puzzle_idx = idx
            self._clear_board()
            
            for i in range(9):
                for j in range(9):
                    ch = puzzle[i*9 + j]
                    if ch.isdigit() and ch != '0':
                        self.cells[i][j].SetValue(ch)
                        self.cells[i][j].SetEditable(False)
                        self.cells[i][j].SetForegroundColour(wx.Colour(20, 120, 115))
                        self._set_cell_color(i, j)
                        self.clues[i][j] = True
                    else:
                        self.cells[i][j].SetEditable(True)
                        self.cells[i][j].SetForegroundColour(wx.Colour(0, 0, 0))
                        self._set_cell_color(i, j)
            
            # Compute solution with fresh solver
            try:
                temp_solver = FastSudokuSolver()
                temp_solver.load_board(puzzle)
                if temp_solver.solve():
                    self.solution = temp_solver.get_solution()
                else:
                    self.solution = None
                    wx.MessageBox("Warning: Could not compute solution for this puzzle.", "Warning", wx.OK|wx.ICON_WARNING)
            except Exception as ex:
                self.solution = None
                wx.MessageBox(f"Warning: Error computing solution: {ex}", "Warning", wx.OK|wx.ICON_WARNING)
            
            self.hints_remaining = self.max_hints
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.difficulty_label.SetLabel(f"Difficulty: {difficulty.title()}")
            self.hints_label.SetLabel(f"({self.hints_remaining}/3)")
            self._update_cells_remaining()
            
            if self.timer_enabled:
                self._reset_timer()
            else:
                self.timer_label.SetLabel("00:00")
        finally:
            self.loading_puzzle = False

    def _on_prev_puzzle(self, event):
        """Load previous puzzle"""
        try:
            self._load_puzzle((self.current_puzzle_idx - 1) % len(PUZZLE_BANK))
        except Exception as e:
            wx.MessageBox(f"Cannot load previous puzzle: {e}", "Error", wx.OK|wx.ICON_ERROR)

    def _on_next_puzzle(self, event):
        """Load next puzzle"""
        try:
            self._load_puzzle((self.current_puzzle_idx + 1) % len(PUZZLE_BANK))
        except Exception as e:
            wx.MessageBox(f"Cannot load next puzzle: {e}", "Error", wx.OK|wx.ICON_ERROR)

    def _on_random_puzzle(self, event):
        """Load random puzzle"""
        try:
            self._load_puzzle(random.randrange(len(PUZZLE_BANK)))
        except Exception as e:
            wx.MessageBox(f"Cannot load random puzzle: {e}", "Error", wx.OK|wx.ICON_ERROR)

    def _on_import_puzzle(self, event):
        """Import custom puzzle"""
        dlg = wx.TextEntryDialog(self, "Enter 81-character puzzle (use . for empty):", "Import Puzzle")
        if dlg.ShowModal() == wx.ID_OK:
            puzzle = dlg.GetValue().strip()
            if len(puzzle) != 81:
                wx.MessageBox("Puzzle must be 81 characters!", "Error", wx.OK|wx.ICON_ERROR)
            elif not all(ch in "0123456789." for ch in puzzle):
                wx.MessageBox("Invalid characters!", "Error", wx.OK|wx.ICON_ERROR)
            else:
                try:
                    test_solver = FastSudokuSolver()
                    test_solver.load_board(puzzle)
                    if test_solver.solve():
                        PUZZLE_BANK.append(("Custom", puzzle))
                        wx.MessageBox("Custom puzzle imported successfully!", "Success", wx.OK|wx.ICON_INFORMATION)
                        self._load_puzzle(len(PUZZLE_BANK) - 1)
                    else:
                        wx.MessageBox("Puzzle has no solution!", "Error", wx.OK|wx.ICON_ERROR)
                except Exception as ex:
                    wx.MessageBox(f"Invalid puzzle: {ex}", "Error", wx.OK|wx.ICON_ERROR)
        dlg.Destroy()

    def _on_hint(self, event):
        """Provide a hint"""
        if self.hints_remaining <= 0:
            wx.MessageBox("No hints remaining!", "Hint", wx.OK|wx.ICON_INFORMATION)
            return
        
        if not self.solution:
            wx.MessageBox("No solution available!", "Error", wx.OK|wx.ICON_ERROR)
            return
        
        empty_cells = [(i, j) for i in range(9) for j in range(9) 
                      if not self.clues[i][j] and not self.cells[i][j].GetValue()]
        
        if not empty_cells:
            wx.MessageBox("No empty cells to hint!", "Hint", wx.OK|wx.ICON_INFORMATION)
            return
        
        i, j = random.choice(empty_cells)
        self.cells[i][j].SetValue(str(self.solution[i][j]))
        self.cells[i][j].SetForegroundColour(wx.Colour(108, 99, 255))
        self._temp_highlight(i, j, wx.Colour(230, 245, 255), 600)
        self.hinted[i][j] = True
        self.hints_remaining -= 1
        self.hints_label.SetLabel(f"({self.hints_remaining}/3)")
        self._update_cells_remaining()

    def _on_undo(self, event):
        """Undo last move"""
        if not self.undo_stack:
            return
        
        row, col, old, new = self.undo_stack.pop()
        self.cells[row][col].SetValue(old)
        self.redo_stack.append((row, col, old, new))
        
        if not self.hinted[row][col]:
            self.cells[row][col].SetEditable(True)
            self._set_cell_color(row, col)
        
        self._update_cells_remaining()

    def _on_redo(self, event):
        """Redo last undone move"""
        if not self.redo_stack:
            return
        
        row, col, old, new = self.redo_stack.pop()
        self.cells[row][col].SetValue(new)
        self.undo_stack.append((row, col, old, new))
        self._update_cells_remaining()

    def _on_solve_play(self, event):
        """Solve the current puzzle in play mode"""
        # Always try to solve from current board state
        try:
            puzzle = ""
            for i in range(9):
                for j in range(9):
                    value = self.cells[i][j].GetValue()
                    puzzle += value if value else "."
            
            temp_solver = FastSudokuSolver()
            temp_solver.load_board(puzzle)
            if temp_solver.solve():
                self.solution = temp_solver.get_solution()
            else:
                wx.MessageBox("Could not solve this puzzle!", "Error", wx.OK|wx.ICON_ERROR)
                return
        except Exception as e:
            wx.MessageBox(f"Error solving puzzle: {e}", "Error", wx.OK|wx.ICON_ERROR)
            return
        
        # Fill all empty cells
        for i in range(9):
            for j in range(9):
                if not self.clues[i][j]:
                    self.cells[i][j].SetValue(str(self.solution[i][j]))
                    self._set_cell_color(i, j)
        
        self._update_cells_remaining()
        self._stop_timer()
        
        wx.MessageBox(
            "✅ Puzzle Solved! ✅\n\nThe board has been completed.",
            "Solved",
            wx.OK|wx.ICON_INFORMATION
        )

    def _update_cells_remaining(self):
        """Update remaining cells counter"""
        try:
            count = sum(1 for i in range(9) for j in range(9) if not self.cells[i][j].GetValue())
            self.cells_label.SetLabel(f"📝 Remaining: {count}")
        except:
            pass

    # ========================================================================
    # TIMER FUNCTIONS
    # ========================================================================

    def _start_timer(self):
        """Start the timer"""
        if not self.timer_enabled:
            return
        self.start_time = time.time()
        self.elapsed_time = 0
        self.timer_running = True
        self._update_timer()

    def _stop_timer(self):
        """Stop the timer"""
        self.timer_running = False
        if self.timer:
            try:
                self.timer.Stop()
            except:
                pass
            self.timer = None

    def _reset_timer(self):
        """Reset the timer"""
        if not self.timer_enabled:
            return
        self._stop_timer()
        self._start_timer()

    def _update_timer(self):
        """Update timer display"""
        if not self.timer_running or not self.timer_enabled:
            return
        
        try:
            self.elapsed_time = int(time.time() - self.start_time)
            if hasattr(self, 'timer_label') and self.timer_label:
                self.timer_label.SetLabel(f"{self._format_time(self.elapsed_time)}")
            self.timer = wx.CallLater(1000, self._update_timer)
        except:
            self.timer_running = False

    def _format_time(self, seconds):
        """Format time as MM:SS"""
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins:02d}:{secs:02d}"

    # ========================================================================
    # UTILITY FUNCTIONS
    # ========================================================================

    def _clear_board(self):
        """Clear the entire board"""
        for i in range(9):
            for j in range(9):
                try:
                    self.cells[i][j].SetValue("")
                    self.cells[i][j].SetEditable(True)
                    self.cells[i][j].SetForegroundColour(wx.Colour(0, 0, 0))
                    self._set_cell_color(i, j)
                    self.clues[i][j] = False
                    self.hinted[i][j] = False
                except:
                    pass
        
        self.solution = None
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._update_cells_remaining()

    def _on_resize(self, event):
        """Handle window resize"""
        try:
            self.Layout()
        except:
            pass
        
        if event is not None:
            event.Skip()

    def _on_close(self, event):
        """Clean up on close"""
        try:
            self._stop_timer()
            if self.solving:
                self.solver.stop()
            self.Destroy()
        except:
            try:
                self.Destroy()
            except:
                pass

# ============================================================================
# MAIN APPLICATION ENTRY POINT
# ============================================================================

def main():
    """Launch the Sudoku application"""
    app = wx.App(False)
    frame = SudokuFrame()
    frame.Show()
    app.MainLoop()

if __name__ == "__main__":
    main()