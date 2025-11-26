from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QSpinBox, 
    QDoubleSpinBox, QCheckBox, QLineEdit, QTextEdit, QPushButton, 
    QGroupBox, QComboBox, QListWidget, QListWidgetItem, QMessageBox,
    QFileDialog, QProgressBar, QTabWidget, QWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
import os
from xml_splitter import XmlSplitConfig, XmlSplitRule
from xml_service import XmlService


class XmlSplitAnalysisThread(QThread):
    """Background thread for analyzing XML structure"""
    analysis_complete = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, xml_content: str, config: XmlSplitConfig):
        super().__init__()
        self.xml_content = xml_content
        self.config = config
        self.xml_service = XmlService()
    
    def run(self):
        """Run the analysis in background thread"""
        try:
            analysis = self.xml_service.analyze_xml_for_splitting(self.xml_content, self.config)
            self.analysis_complete.emit(analysis)
        except Exception as e:
            self.error_occurred.emit(str(e))


class XmlSplitConfigDialog(QDialog):
    """Dialog for configuring XML splitting parameters"""
    
    def __init__(self, parent=None, xml_content: str = None):
        super().__init__(parent)
        self.xml_content = xml_content
        self.xml_service = XmlService()
        self.analysis_thread = None
        self.analysis_result = None
        
        self.setWindowTitle("XML Split Configuration")
        self.setModal(True)
        self.resize(600, 500)
        
        # Apply VSCode-like styling
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #cccccc;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3c3c3c;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #0e639c;
                border: none;
                padding: 8px 16px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QSpinBox, QDoubleSpinBox, QLineEdit, QComboBox {
                background-color: #3c3c3c;
                border: 1px solid #5a5a5a;
                padding: 4px;
                border-radius: 3px;
            }
            QTextEdit {
                background-color: #2d2d30;
                border: 1px solid #5a5a5a;
                border-radius: 3px;
            }
            QListWidget {
                background-color: #2d2d30;
                border: 1px solid #5a5a5a;
                border-radius: 3px;
            }
            QTabWidget::pane {
                border: 1px solid #5a5a5a;
                background-color: #2d2d30;
            }
            QTabBar::tab {
                background-color: #3c3c3c;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #0e639c;
            }
        """)
        
        self.setup_ui()
        self.load_default_config()
        
        if self.xml_content:
            self.analyze_xml()
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Create tab widget for different configuration sections
        self.tab_widget = QTabWidget()
        
        # Basic Configuration Tab
        basic_tab = QWidget()
        self.setup_basic_tab(basic_tab)
        self.tab_widget.addTab(basic_tab, "Basic Settings")
        
        # Advanced Configuration Tab
        advanced_tab = QWidget()
        self.setup_advanced_tab(advanced_tab)
        self.tab_widget.addTab(advanced_tab, "Advanced Rules")
        
        # Analysis Results Tab
        analysis_tab = QWidget()
        self.setup_analysis_tab(analysis_tab)
        self.tab_widget.addTab(analysis_tab, "Analysis")
        
        layout.addWidget(self.tab_widget)
        
        # Progress bar for analysis
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        self.analyze_btn = QPushButton("Analyze XML")
        self.analyze_btn.clicked.connect(self.analyze_xml)
        button_layout.addWidget(self.analyze_btn)
        
        button_layout.addStretch()
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def setup_basic_tab(self, tab):
        """Setup basic configuration tab"""
        layout = QVBoxLayout(tab)
        
        # Threshold Configuration Group
        threshold_group = QGroupBox("Threshold-Based Splitting")
        threshold_layout = QFormLayout(threshold_group)
        
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(1.0, 50.0)
        self.threshold_spin.setValue(15.0)
        self.threshold_spin.setSuffix("%")
        self.threshold_spin.setToolTip("Percentage threshold for upper-level elements to trigger new chapter")
        threshold_layout.addRow("Threshold Percentage:", self.threshold_spin)
        
        self.upper_levels_edit = QLineEdit("2,3")
        self.upper_levels_edit.setToolTip("Comma-separated list of XML levels to consider (e.g., 2,3)")
        threshold_layout.addRow("Upper Levels:", self.upper_levels_edit)
        
        layout.addWidget(threshold_group)
        
        # Output Configuration Group
        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout(output_group)
        
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Select output directory...")
        output_dir_layout = QHBoxLayout()
        output_dir_layout.addWidget(self.output_dir_edit)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_output_directory)
        output_dir_layout.addWidget(browse_btn)
        
        output_layout.addRow("Output Directory:", output_dir_layout)
        
        self.create_backup_cb = QCheckBox("Create backup of original file")
        self.create_backup_cb.setChecked(True)
        output_layout.addRow(self.create_backup_cb)
        
        layout.addWidget(output_group)
        
        layout.addStretch()
    
    def setup_advanced_tab(self, tab):
        """Setup advanced configuration tab"""
        layout = QVBoxLayout(tab)
        
        # Additional Rules Group
        rules_group = QGroupBox("Additional Split Rules")
        rules_layout = QVBoxLayout(rules_group)
        
        # Element-based splitting
        element_layout = QHBoxLayout()
        self.element_cb = QCheckBox("Split by element type:")
        element_layout.addWidget(self.element_cb)
        
        self.element_edit = QLineEdit()
        self.element_edit.setPlaceholderText("e.g., chapter, section")
        self.element_edit.setEnabled(False)
        element_layout.addWidget(self.element_edit)
        
        self.element_cb.toggled.connect(self.element_edit.setEnabled)
        rules_layout.addLayout(element_layout)
        
        # Depth-based splitting
        depth_layout = QHBoxLayout()
        self.depth_cb = QCheckBox("Split by maximum depth:")
        depth_layout.addWidget(self.depth_cb)
        
        self.depth_spin = QSpinBox()
        self.depth_spin.setRange(1, 20)
        self.depth_spin.setValue(5)
        self.depth_spin.setEnabled(False)
        depth_layout.addWidget(self.depth_spin)
        
        self.depth_cb.toggled.connect(self.depth_spin.setEnabled)
        rules_layout.addLayout(depth_layout)
        
        # Size-based splitting
        size_layout = QHBoxLayout()
        self.size_cb = QCheckBox("Split by file size:")
        size_layout.addWidget(self.size_cb)
        
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 1000)
        self.size_spin.setValue(100)
        self.size_spin.setSuffix(" KB")
        self.size_spin.setEnabled(False)
        size_layout.addWidget(self.size_spin)
        
        self.size_cb.toggled.connect(self.size_spin.setEnabled)
        rules_layout.addLayout(size_layout)
        
        # XPath-based splitting
        xpath_layout = QVBoxLayout()
        self.xpath_cb = QCheckBox("Split by XPath expression:")
        xpath_layout.addWidget(self.xpath_cb)
        
        self.xpath_edit = QTextEdit()
        self.xpath_edit.setMaximumHeight(80)
        self.xpath_edit.setPlaceholderText("Enter XPath expression...")
        self.xpath_edit.setEnabled(False)
        xpath_layout.addWidget(self.xpath_edit)
        
        self.xpath_cb.toggled.connect(self.xpath_edit.setEnabled)
        rules_layout.addLayout(xpath_layout)
        
        layout.addWidget(rules_group)
        
        layout.addStretch()
    
    def setup_analysis_tab(self, tab):
        """Setup analysis results tab"""
        layout = QVBoxLayout(tab)
        
        # Analysis Results Group
        results_group = QGroupBox("XML Structure Analysis")
        results_layout = QVBoxLayout(results_group)
        
        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setPlaceholderText("Click 'Analyze XML' to see structure analysis...")
        results_layout.addWidget(self.analysis_text)
        
        layout.addWidget(results_group)
        
        # Recommendations Group
        recommendations_group = QGroupBox("Split Recommendations")
        recommendations_layout = QVBoxLayout(recommendations_group)
        
        self.recommendations_list = QListWidget()
        recommendations_layout.addWidget(self.recommendations_list)
        
        layout.addWidget(recommendations_group)
    
    def load_default_config(self):
        """Load default configuration values"""
        # Set default output directory to current directory + "_split"
        if self.xml_content:
            default_dir = os.path.join(os.getcwd(), "xml_split_output")
            self.output_dir_edit.setText(default_dir)
    
    def browse_output_directory(self):
        """Browse for output directory"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", self.output_dir_edit.text()
        )
        if directory:
            self.output_dir_edit.setText(directory)
    
    def analyze_xml(self):
        """Analyze XML structure in background thread"""
        if not self.xml_content:
            QMessageBox.warning(self, "Warning", "No XML content available for analysis.")
            return
        
        # Create configuration from current settings
        config = self.get_split_config()
        
        # Start analysis thread
        self.analysis_thread = XmlSplitAnalysisThread(self.xml_content, config)
        self.analysis_thread.analysis_complete.connect(self.on_analysis_complete)
        self.analysis_thread.error_occurred.connect(self.on_analysis_error)
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.analyze_btn.setEnabled(False)
        
        self.analysis_thread.start()
    
    def on_analysis_complete(self, analysis: dict):
        """Handle completed analysis"""
        self.analysis_result = analysis
        
        # Update analysis text
        analysis_text = self.format_analysis_result(analysis)
        self.analysis_text.setPlainText(analysis_text)
        
        # Update recommendations
        self.update_recommendations(analysis)
        
        # Hide progress and re-enable button
        self.progress_bar.setVisible(False)
        self.analyze_btn.setEnabled(True)
        
        # Switch to analysis tab
        self.tab_widget.setCurrentIndex(2)
    
    def on_analysis_error(self, error: str):
        """Handle analysis error"""
        self.progress_bar.setVisible(False)
        self.analyze_btn.setEnabled(True)
        
        QMessageBox.critical(self, "Analysis Error", f"Failed to analyze XML:\n{error}")
    
    def format_analysis_result(self, analysis: dict) -> str:
        """Format analysis result for display"""
        lines = []
        lines.append("XML Structure Analysis")
        lines.append("=" * 30)
        lines.append("")
        
        # Total elements
        if 'total_elements' in analysis:
            lines.append(f"Total Elements: {analysis['total_elements']}")
        
        # Elements by level (support both legacy key and new key)
        counts_by_level = analysis.get('element_counts_by_level') or analysis.get('elements_by_level') or {}
        if counts_by_level:
            # Compute and show maximum depth if not provided by analysis
            max_depth = max(counts_by_level.keys()) if counts_by_level else 0
            lines.append(f"Maximum Depth: {analysis.get('max_depth', max_depth)}")
            
            lines.append("\nElements by Level:")
            for level in sorted(counts_by_level.keys()):
                count = counts_by_level[level]
                lines.append(f"  Level {level}: {count} elements")
        
        # Threshold analysis details (per-level)
        if 'threshold_analysis' in analysis:
            threshold_info = analysis['threshold_analysis'] or {}
            lines.append("\nThreshold Analysis:")
            lines.append(f"  Configured Threshold: {threshold_info.get('threshold_percentage', 0)}%")
            lines.append(f"  Upper Levels: {', '.join(map(str, threshold_info.get('upper_levels', [])))}")
            level_analysis = threshold_info.get('level_analysis', {})
            for level in sorted(level_analysis.keys()):
                la = level_analysis[level]
                lines.append(
                    f"  Level {level}: {la.get('element_count', 0)} elements "
                    f"({la.get('percentage_of_total', 0):.1f}%), "
                    f"exceeds threshold: {'Yes' if la.get('exceeds_threshold', False) else 'No'}"
                )
            # Summary of levels recommended for splitting
            recommended_levels = [lvl for lvl, la in level_analysis.items() if la.get('recommended_for_splitting')]
            if recommended_levels:
                lines.append(f"  Recommended Levels for Splitting: {', '.join(map(str, sorted(recommended_levels)))}")
            else:
                lines.append("  No levels exceed the threshold.")
        
        # Recommended split points count
        if 'recommended_splits' in analysis:
            lines.append(f"\nRecommended Split Points: {len(analysis['recommended_splits'])}")
        
        return "\n".join(lines)
    
    def update_recommendations(self, analysis: dict):
        """Update recommendations list"""
        self.recommendations_list.clear()
        
        # Threshold-based recommendation summary
        threshold_info = analysis.get('threshold_analysis', {}) or {}
        level_analysis = threshold_info.get('level_analysis', {})
        recommended_levels = [lvl for lvl, la in level_analysis.items() if la.get('recommended_for_splitting')]
        if threshold_info:
            if recommended_levels:
                item = QListWidgetItem(
                    f"✓ Threshold-based splitting recommended at levels: {', '.join(map(str, sorted(recommended_levels)))}"
                )
                # Tooltip shows percentages for recommended levels
                percent_desc = ", ".join(
                    [f"L{lvl}({level_analysis[lvl].get('percentage_of_total', 0):.1f}%)" for lvl in sorted(recommended_levels)]
                )
                item.setToolTip(
                    f"Threshold {threshold_info.get('threshold_percentage', 0)}% exceeded: {percent_desc}"
                )
                self.recommendations_list.addItem(item)
            else:
                item = QListWidgetItem("○ Threshold-based splitting not needed")
                item.setToolTip("Upper levels are below threshold")
                self.recommendations_list.addItem(item)
        
        # Count of recommended split points
        if 'recommended_splits' in analysis and analysis['recommended_splits']:
            item = QListWidgetItem(f"✓ {len(analysis['recommended_splits'])} split points identified")
            self.recommendations_list.addItem(item)
        
        # Depth alert
        counts_by_level = analysis.get('element_counts_by_level') or analysis.get('elements_by_level') or {}
        max_depth = max(counts_by_level.keys()) if counts_by_level else analysis.get('max_depth', 0)
        if max_depth and max_depth > 10:
            item = QListWidgetItem("⚠ Consider depth-based splitting (deep nesting detected)")
            self.recommendations_list.addItem(item)
    
    def get_split_config(self) -> XmlSplitConfig:
        """Get split configuration from dialog settings"""
        # Parse upper levels
        upper_levels_text = self.upper_levels_edit.text().strip()
        try:
            upper_levels = [int(x.strip()) for x in upper_levels_text.split(',') if x.strip()]
        except ValueError:
            upper_levels = [2, 3]  # Default fallback
        
        # Create base configuration
        config = XmlSplitConfig(
            threshold_percentage=self.threshold_spin.value(),
            upper_levels=upper_levels
        )
        
        # Add additional rules if enabled
        if self.element_cb.isChecked() and self.element_edit.text().strip():
            elements = [x.strip() for x in self.element_edit.text().split(',') if x.strip()]
            for element in elements:
                config.add_rule(XmlSplitRule.create_element_rule(element))
        
        if self.depth_cb.isChecked():
            config.add_rule(XmlSplitRule.create_depth_rule(self.depth_spin.value()))
        
        if self.size_cb.isChecked():
            config.add_rule(XmlSplitRule.create_size_rule(self.size_spin.value() * 1024))  # Convert KB to bytes
        
        if self.xpath_cb.isChecked() and self.xpath_edit.toPlainText().strip():
            config.add_rule(XmlSplitRule.create_xpath_rule(self.xpath_edit.toPlainText().strip()))
        
        return config
    
    def get_output_directory(self) -> str:
        """Get selected output directory"""
        return self.output_dir_edit.text().strip()
    
    def should_create_backup(self) -> bool:
        """Check if backup should be created"""
        return self.create_backup_cb.isChecked()
    
    def get_analysis_result(self) -> dict:
        """Get the analysis result"""
        return self.analysis_result