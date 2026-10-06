#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import os
import tempfile

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf

from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader


APP_TITLE = "Impressor de Pôsteres"
A4_W, A4_H = A4
MM = 72.0 / 25.4


class PosterApp(Gtk.Window):
    def __init__(self):
        super().__init__(title=APP_TITLE)
        self.set_default_size(980, 700)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(12)

        self.image_path = None
        self.image = None
        self.preview_pixbuf = None

        self.build_interface()

    def build_interface(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(root)

        # Cabeçalho
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        root.pack_start(header, False, False, 0)

        title = Gtk.Label()
        title.set_markup("<span size='18000' weight='bold'>Impressor de Pôsteres</span>")
        title.set_xalign(0)
        header.pack_start(title, False, False, 0)

        subtitle = Gtk.Label(
            label="Divida uma imagem em várias folhas A4, visualize a montagem e gere um PDF."
        )
        subtitle.set_xalign(0)
        header.pack_start(subtitle, False, False, 0)

        # Área principal: controles + preview
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        root.pack_start(content, True, True, 0)

        controls = Gtk.Frame(label=" Configurações ")
        controls.set_size_request(300, -1)
        content.pack_start(controls, False, False, 0)

        grid = Gtk.Grid()
        grid.set_border_width(12)
        grid.set_row_spacing(10)
        grid.set_column_spacing(8)
        controls.add(grid)

        row = 0

        self.open_button = Gtk.Button(label="Abrir imagem")
        self.open_button.connect("clicked", self.open_image)
        grid.attach(self.open_button, 0, row, 2, 1)
        row += 1

        self.file_label = Gtk.Label(label="Nenhuma imagem selecionada")
        self.file_label.set_xalign(0)
        self.file_label.set_line_wrap(True)
        grid.attach(self.file_label, 0, row, 2, 1)
        row += 1

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        grid.attach(sep, 0, row, 2, 1)
        row += 1

        label = Gtk.Label(label="Divisão do pôster:")
        label.set_xalign(0)
        grid.attach(label, 0, row, 2, 1)
        row += 1

        self.division_combo = Gtk.ComboBoxText()

        # 1x1 até 10x10
        for cols in range(1, 11):
            for rows in range(1, 11):
                self.division_combo.append_text(f"{cols} x {rows}")

        # Seleção inicial: 2 x 1
        self.division_combo.set_active(self.division_index(2, 1))
        self.division_combo.connect("changed", self.settings_changed)
        grid.attach(self.division_combo, 0, row, 2, 1)
        row += 1

        self.pages_label = Gtk.Label()
        self.pages_label.set_markup("<b>Total de folhas: 2</b>")
        self.pages_label.set_xalign(0)
        grid.attach(self.pages_label, 0, row, 2, 1)
        row += 1

        label = Gtk.Label(label="Orientação:")
        label.set_xalign(0)
        grid.attach(label, 0, row, 1, 1)

        self.orientation_combo = Gtk.ComboBoxText()
        self.orientation_combo.append_text("Retrato")
        self.orientation_combo.append_text("Paisagem")
        self.orientation_combo.set_active(0)
        self.orientation_combo.connect("changed", self.settings_changed)
        grid.attach(self.orientation_combo, 1, row, 1, 1)
        row += 1

        label = Gtk.Label(label="Sobreposição (mm):")
        label.set_xalign(0)
        grid.attach(label, 0, row, 1, 1)

        self.overlap_spin = Gtk.SpinButton.new_with_range(0, 30, 1)
        self.overlap_spin.set_value(5)
        self.overlap_spin.connect("value-changed", self.settings_changed)
        grid.attach(self.overlap_spin, 1, row, 1, 1)
        row += 1

        self.cut_marks = Gtk.CheckButton(label="Marcas de corte")
        self.cut_marks.set_active(True)
        self.cut_marks.connect("toggled", self.settings_changed)
        grid.attach(self.cut_marks, 0, row, 2, 1)
        row += 1

        self.page_numbers = Gtk.CheckButton(label="Número das folhas")
        self.page_numbers.set_active(True)
        self.page_numbers.connect("toggled", self.settings_changed)
        grid.attach(self.page_numbers, 0, row, 2, 1)
        row += 1

        info = Gtk.Label()
        info.set_markup(
            "<small><b>Exemplo:</b> 2 x 3 = 2 folhas de largura × "
            "3 folhas de altura = 6 páginas A4.</small>"
        )
        info.set_xalign(0)
        info.set_line_wrap(True)
        grid.attach(info, 0, row, 2, 1)
        row += 1

        # Preview
        preview_frame = Gtk.Frame(label=" Visualização ")
        content.pack_start(preview_frame, True, True, 0)

        self.preview = Gtk.DrawingArea()
        self.preview.set_size_request(500, 450)
        self.preview.set_hexpand(True)
        self.preview.set_vexpand(True)
        self.preview.connect("draw", self.draw_preview)
        preview_frame.add(self.preview)

        # Rodapé
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        root.pack_start(footer, False, False, 0)

        self.status = Gtk.Label(label="Selecione uma imagem para começar.")
        self.status.set_xalign(0)
        footer.pack_start(self.status, True, True, 0)

        self.generate_button = Gtk.Button(label="Gerar PDF A4")
        self.generate_button.set_sensitive(False)
        self.generate_button.connect("clicked", self.generate_pdf_dialog)
        footer.pack_end(self.generate_button, False, False, 0)

    def division_index(self, cols, rows):
        return (cols - 1) * 10 + (rows - 1)

    def get_division(self):
        text = self.division_combo.get_active_text() or "2 x 1"
        cols, rows = [int(x.strip()) for x in text.split("x")]
        return cols, rows

    def get_page_size(self):
        if self.orientation_combo.get_active() == 1:
            return A4_H, A4_W
        return A4_W, A4_H

    def settings_changed(self, *_args):
        cols, rows = self.get_division()
        self.pages_label.set_markup(
            f"<b>Total de folhas: {cols * rows}</b>"
        )
        self.preview.queue_draw()

    def open_image(self, _button):
        dialog = Gtk.FileChooserDialog(
            title="Selecionar imagem",
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK,
        )

        filt = Gtk.FileFilter()
        filt.set_name("Imagens")
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp", "*.tif", "*.tiff"):
            filt.add_pattern(ext)
        dialog.add_filter(filt)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            path = dialog.get_filename()
            try:
                img = Image.open(path)
                img.load()
                if img.width < 1 or img.height < 1:
                    raise ValueError("A imagem não possui dimensões válidas.")

                self.image_path = path
                self.image = img.convert("RGB")

                filename = os.path.basename(path)
                self.file_label.set_text(
                    f"{filename}\n{self.image.width} × {self.image.height} px"
                )
                self.status.set_text("Imagem carregada. Configure a divisão e gere o PDF.")
                self.generate_button.set_sensitive(True)
                self.preview.queue_draw()

            except Exception as exc:
                self.error(f"Não foi possível abrir a imagem:\n{exc}")

        dialog.destroy()

    def draw_preview(self, widget, cr):
        allocation = widget.get_allocation()
        w = allocation.width
        h = allocation.height

        # Fundo
        cr.set_source_rgb(0.94, 0.94, 0.94)
        cr.paint()

        if not self.image:
            cr.set_source_rgb(0.35, 0.35, 0.35)
            cr.select_font_face("Sans", 0, 0)
            cr.set_font_size(18)
            text = "Selecione uma imagem"
            ext = cr.text_extents(text)
            cr.move_to((w - ext.width) / 2, (h - ext.height) / 2)
            cr.show_text(text)
            return

        cols, rows = self.get_division()

        # Área do pôster, mantendo a proporção da imagem.
        margin = 35
        available_w = max(100, w - 2 * margin)
        available_h = max(100, h - 2 * margin)

        image_ratio = self.image.width / self.image.height
        poster_ratio = image_ratio

        poster_w = available_w
        poster_h = poster_w / poster_ratio

        if poster_h > available_h:
            poster_h = available_h
            poster_w = poster_h * poster_ratio

        x = (w - poster_w) / 2
        y = (h - poster_h) / 2

        # Desenhar a imagem
        try:
            thumb = self.image.copy()
            thumb.thumbnail((int(poster_w), int(poster_h)), Image.Resampling.LANCZOS)

            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.close()
            thumb.save(tmp.name, "PNG")

            pixbuf = GdkPixbuf.Pixbuf.new_from_file(tmp.name)

            iw = pixbuf.get_width()
            ih = pixbuf.get_height()
            scale = min(poster_w / iw, poster_h / ih)
            dw = iw * scale
            dh = ih * scale
            ix = x + (poster_w - dw) / 2
            iy = y + (poster_h - dh) / 2

            Gdk.cairo_set_source_pixbuf(cr, pixbuf, ix, iy)
            cr.paint()

            os.unlink(tmp.name)
        except Exception:
            cr.set_source_rgb(0.8, 0.8, 0.8)
            cr.rectangle(x, y, poster_w, poster_h)
            cr.fill()

        # Grade
        cr.set_line_width(1.2)
        cr.set_source_rgb(0.1, 0.3, 0.8)

        for c in range(1, cols):
            gx = x + poster_w * c / cols
            cr.move_to(gx, y)
            cr.line_to(gx, y + poster_h)
            cr.stroke()

        for r in range(1, rows):
            gy = y + poster_h * r / rows
            cr.move_to(x, gy)
            cr.line_to(x + poster_w, gy)
            cr.stroke()

        # Borda
        cr.set_line_width(2)
        cr.set_source_rgb(0.1, 0.1, 0.1)
        cr.rectangle(x, y, poster_w, poster_h)
        cr.stroke()

        # Número de cada folha
        cr.select_font_face("Sans", 0, 1)
        cr.set_font_size(max(10, min(16, 180 / max(cols, rows))))
        page = 1

        for r in range(rows):
            for c in range(cols):
                cx = x + poster_w * (c + 0.5) / cols
                cy = y + poster_h * (r + 0.5) / rows
                text = str(page)
                ext = cr.text_extents(text)

                cr.set_source_rgba(1, 1, 1, 0.75)
                cr.rectangle(
                    cx - ext.width / 2 - 5,
                    cy - ext.height - 4,
                    ext.width + 10,
                    ext.height + 8
                )
                cr.fill()

                cr.set_source_rgb(0.05, 0.05, 0.05)
                cr.move_to(cx - ext.width / 2, cy)
                cr.show_text(text)
                page += 1

        # Texto inferior
        cr.set_source_rgb(0.2, 0.2, 0.2)
        cr.select_font_face("Sans", 0, 0)
        cr.set_font_size(12)
        text = f"{cols} x {rows}  •  {cols * rows} folhas A4"
        ext = cr.text_extents(text)
        cr.move_to((w - ext.width) / 2, h - 10)
        cr.show_text(text)

    def generate_pdf_dialog(self, _button):
        if not self.image:
            self.error("Selecione uma imagem primeiro.")
            return

        dialog = Gtk.FileChooserDialog(
            title="Salvar PDF do pôster",
            parent=self,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK,
        )
        dialog.set_current_name("poster.pdf")

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            path = dialog.get_filename()
            if not path.lower().endswith(".pdf"):
                path += ".pdf"

            try:
                self.create_pdf(path)
                self.status.set_text(
                    f"PDF criado com {self.get_division()[0] * self.get_division()[1]} folhas A4."
                )
                self.info(f"PDF gerado com sucesso:\n{path}")
            except Exception as exc:
                self.error(f"Erro ao gerar o PDF:\n{exc}")

        dialog.destroy()

    def create_pdf(self, output):
        img = self.image
        cols, rows = self.get_division()
        page_w, page_h = self.get_page_size()

        overlap = self.overlap_spin.get_value() * MM
        draw_cut_marks = self.cut_marks.get_active()
        draw_numbers = self.page_numbers.get_active()

        total_w = cols * page_w
        total_h = rows * page_h

        iw, ih = img.size

        # Ajusta a imagem para preencher o pôster sem deformar.
        scale = min(total_w / iw, total_h / ih)
        draw_w = iw * scale
        draw_h = ih * scale

        offset_x = (total_w - draw_w) / 2
        offset_y = (total_h - draw_h) / 2

        pdf = canvas.Canvas(output, pagesize=(page_w, page_h))

        page_number = 1

        for row in range(rows):
            for col in range(cols):
                # Coordenadas da folha no pôster.
                left = col * page_w
                bottom = total_h - (row + 1) * page_h

                # Região do pôster que será colocada nesta folha.
                crop_left = max(0, left - overlap)
                crop_right = min(total_w, left + page_w + overlap)
                crop_bottom = max(0, bottom - overlap)
                crop_top = min(total_h, bottom + page_h + overlap)

                # Converte para coordenadas da imagem.
                src_left = (crop_left - offset_x) / scale
                src_right = (crop_right - offset_x) / scale
                src_bottom = (crop_bottom - offset_y) / scale
                src_top = (crop_top - offset_y) / scale

                src_left = max(0, src_left)
                src_right = min(iw, src_right)
                src_bottom = max(0, src_bottom)
                src_top = min(ih, src_top)

                if src_right > src_left and src_top > src_bottom:
                    crop = img.crop((
                        int(src_left),
                        int(ih - src_top),
                        int(src_right),
                        int(ih - src_bottom),
                    ))

                    temp = tempfile.NamedTemporaryFile(
                        suffix=".jpg", delete=False
                    )
                    temp.close()

                    crop.save(temp.name, "JPEG", quality=96)

                    # Posição do crop dentro da folha.
                    dx = left - crop_left
                    dy = bottom - crop_bottom

                    dw = (src_right - src_left) * scale
                    dh = (src_top - src_bottom) * scale

                    pdf.drawImage(
                        ImageReader(temp.name),
                        dx,
                        dy,
                        width=dw,
                        height=dh,
                        preserveAspectRatio=True,
                        mask="auto",
                    )

                    os.unlink(temp.name)

                # Borda da folha.
                if draw_cut_marks:
                    pdf.setLineWidth(0.5)
                    pdf.rect(0, 0, page_w, page_h)

                if draw_numbers:
                    pdf.setFont("Helvetica", 7)
                    pdf.drawString(
                        10,
                        10,
                        f"Pôster — folha {page_number}/{cols * rows}"
                    )

                pdf.showPage()
                page_number += 1

        pdf.save()

    def error(self, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Erro",
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def info(self, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Concluído",
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()


def main():
    app = PosterApp()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
