"""Small focus-session picker, opened only by an explicit reading shortcut."""

import curses


def choose_focus(screen, mode='timer', minutes=5):
    minutes = max(5, minutes)
    while True:
        screen.erase()
        height, width = screen.getmaxyx()
        lines = [
            'Focus de lecture', '',
            ('› ' if mode == 'chrono' else '  ') + 'c : Chrono · temps écoulé',
            ('› ' if mode == 'timer' else '  ') + 'm : Minuteur · temps restant', '',
            f'Durée du minuteur : {minutes} min (minimum 5)',
            'j / k : − / + 5 min · flèches : choisir le mode', '',
            'Entrée : démarrer · f / Échap : annuler',
        ]
        if height < 10:
            lines = ['Focus · c chrono / m minuteur', f'Minuteur : {minutes} min · j/k régler',
                     'Entrée démarrer · Échap annuler']
        for row, line in enumerate(lines[:max(0, height - 1)]):
            try:
                screen.addstr(row, 0, line[:max(0, width - 1)], curses.A_BOLD if row == 0 else 0)
            except curses.error:
                pass
        screen.refresh()
        key = screen.getch()
        if key in (27, ord('f'), ord('q')):
            return None
        if key in (10, 13, curses.KEY_ENTER):
            return mode, minutes
        if key == ord('c'):
            mode = 'chrono'
        elif key == ord('m'):
            mode = 'timer'
        elif key in (curses.KEY_UP, curses.KEY_DOWN):
            mode = 'chrono' if mode == 'timer' else 'timer'
        elif key == ord('j'):
            minutes = max(5, minutes - 5)
        elif key == ord('k'):
            minutes += 5
