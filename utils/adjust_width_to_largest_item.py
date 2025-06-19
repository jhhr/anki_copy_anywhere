from aqt.qt import QComboBox, QFontMetrics


def adjust_width_to_largest_item(combo_box: QComboBox):
    """Adjusts the width of a standard combo box to the largest item"""
    max_width = 0
    for i in range(combo_box.count()):
        item_text = combo_box.itemText(i)
        item_width = QFontMetrics(combo_box.font()).horizontalAdvance(item_text)
        if item_width > max_width:
            max_width = item_width
    view = combo_box.view()
    if view is not None:
        view.setMinimumWidth(max_width + 20)
