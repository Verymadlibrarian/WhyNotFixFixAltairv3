import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFileDialog, QTextEdit, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal


class ASSProcessorWorker(QThread):
    """Worker thread pour exécuter le traitement sans bloquer l'interface GUI."""
    progress = pyqtSignal(int)
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int, int)

    def __init__(self, input_dir: str, output_dir: str):
        super().__init__()
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)

    def run(self):
        ass_files = list(self.input_dir.glob("*.ass"))
        total_files = len(ass_files)

        if total_files == 0:
            self.finished_signal.emit(0, 0)
            return

        os.makedirs(self.output_dir, exist_ok=True)
        processed_count = 0

        for idx, file_path in enumerate(ass_files, 1):
            out_file = self.output_dir / file_path.name
            removed_lines = self.filter_forced_subs(file_path, out_file)
            
            self.log_signal.emit(f" Traité: {file_path.name} ({removed_lines} lignes 'Default' supprimées)")
            processed_count += 1
            self.progress.emit(int((idx / total_files) * 100))

        self.finished_signal.emit(processed_count, total_files)

    def filter_forced_subs(self, input_file: Path, output_file: Path) -> int:
        output_lines = []
        removed_count = 0

        with open(input_file, "r", encoding="utf-8-sig", errors="ignore") as f:
            for line in f:
                if line.startswith("Dialogue:"):
                    parts = line.split(",", 9)
                    if len(parts) >= 4:
                        style_name = parts[3].strip()
                        # Filtre les lignes ayant le style "Default" (minuscule ou majuscule)
                        if style_name.lower() == "default":
                            removed_count += 1
                            continue

                output_lines.append(line)

        with open(output_file, "w", encoding="utf-8") as f:
            f.writelines(output_lines)

        return removed_count


class ASSCleanerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("ASS Forced Subtitle Cleaner")
        self.resize(600, 450)

        main_layout = QVBoxLayout()

        # Dossier d'entrée
        in_layout = QHBoxLayout()
        self.in_label = QLabel("Dossier d'entrée :")
        self.in_label.setFixedWidth(120)
        self.in_input = QLineEdit()
        self.in_btn = QPushButton("Parcourir...")
        self.in_btn.clicked.connect(self.browse_input)
        in_layout.addWidget(self.in_label)
        in_layout.addWidget(self.in_input)
        in_layout.addWidget(self.in_btn)
        main_layout.addLayout(in_layout)

        # Dossier de sortie
        out_layout = QHBoxLayout()
        self.out_label = QLabel("Dossier de sortie :")
        self.out_label.setFixedWidth(120)
        self.out_input = QLineEdit()
        self.out_btn = QPushButton("Parcourir...")
        self.out_btn.clicked.connect(self.browse_output)
        out_layout.addWidget(self.out_label)
        out_layout.addWidget(self.out_input)
        out_layout.addWidget(self.out_btn)
        main_layout.addLayout(out_layout)

        # Bouton Lancer
        self.start_btn = QPushButton("Nettoyer les fichiers .ass")
        self.start_btn.setStyleSheet("font-weight: bold; font-size: 14px; padding: 8px;")
        self.start_btn.clicked.connect(self.start_processing)
        main_layout.addWidget(self.start_btn)

        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # Zone de Log / Console
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        main_layout.addWidget(self.log_box)

        self.setLayout(main_layout)

    def browse_input(self):
        folder = QFileDialog.getExistingDirectory(self, "Sélectionner le dossier d'entrée")
        if folder:
            self.in_input.setText(folder)
            # Met par défaut un sous-dossier /forced_only dans le dossier de sortie
            if not self.out_input.text():
                self.out_input.setText(os.path.join(folder, "forced_only"))

    def browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Sélectionner le dossier de sortie")
        if folder:
            self.out_input.setText(folder)

    def start_processing(self):
        input_dir = self.in_input.text().strip()
        output_dir = self.out_input.text().strip()

        if not input_dir or not os.path.exists(input_dir):
            QMessageBox.warning(self, "Erreur", "Veuillez sélectionner un dossier d'entrée valide.")
            return

        if not output_dir:
            QMessageBox.warning(self, "Erreur", "Veuillez spécifier un dossier de sortie.")
            return

        if os.path.abspath(input_dir) == os.path.abspath(output_dir):
            QMessageBox.warning(self, "Attention", "Le dossier de sortie doit être différent du dossier d'entrée pour éviter d'écraser les originaux.")
            return

        # Désactiver les contrôles pendant le traitement
        self.start_btn.setEnabled(False)
        self.in_btn.setEnabled(False)
        self.out_btn.setEnabled(False)
        self.log_box.clear()
        self.progress_bar.setValue(0)

        # Lancer le thread de traitement
        self.worker = ASSProcessorWorker(input_dir, output_dir)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.log_signal.connect(self.log_box.append)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, count: int, total: int):
        self.start_btn.setEnabled(True)
        self.in_btn.setEnabled(True)
        self.out_btn.setEnabled(True)

        if total == 0:
            QMessageBox.information(self, "Information", "Aucun fichier .ass trouvé dans le dossier d'entrée.")
        else:
            QMessageBox.information(self, "Terminé", f"Traitement terminé avec succès !\n\n{count}/{total} fichiers ont été traités.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ASSCleanerApp()
    window.show()
    sys.exit(app.exec())