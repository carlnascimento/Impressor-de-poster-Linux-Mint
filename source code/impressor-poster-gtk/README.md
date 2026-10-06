# Impressor de Pôsteres — GTK

Versão 1.1.0.

A interface foi projetada para funcionar de maneira semelhante ao recurso
de impressão de pôster encontrado em drivers de impressoras no Windows.

## Divisão

O menu "Divisão do pôster" possui opções de:

- 1 x 1
- 1 x 2
- ...
- 2 x 1
- 2 x 2
- 2 x 3
- 2 x 4
- 2 x 5
- ...
- 10 x 10

Exemplo:

**2 x 3 = 2 folhas na largura × 3 folhas na altura = 6 páginas A4.**

## Instalar dependências no Linux Mint

```bash
sudo apt update
sudo apt install python3 python3-gi gir1.2-gtk-3.0 python3-pil python3-reportlab python3-cairo
```

## Testar

```bash
python3 src/main.py
```

## Criar o .deb

```bash
sudo apt install build-essential debhelper
chmod +x debian/rules
dpkg-buildpackage -us -uc -b
```

O `.deb` aparecerá na pasta acima do projeto.

Instalar:

```bash
sudo dpkg -i ../impressor-poster_1.1.0-1_all.deb
sudo apt -f install
```

## Recursos

- Interface GTK em português.
- Menu de divisão do pôster.
- Divisões de 1x1 até 10x10.
- Cálculo automático de páginas.
- Preview visual.
- Orientação retrato/paisagem.
- Sobreposição configurável.
- Marcas de corte.
- Numeração das folhas.
- Geração de PDF A4.
