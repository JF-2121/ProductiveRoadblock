import 'dart:math';

import 'package:flutter/material.dart';

/// A grid of square tiles that fills the available space, keeping every
/// tile at least 1cm x 1cm; if that would make the grid taller than the
/// screen has room for, it scrolls instead of squishing tiles smaller.
/// Shared by [PianoTilesGame] and [SimonSaysGame] so both "Roadblock"
/// minigames render their 2x4x4 (32-tile) board identically.
class SquareTileGrid extends StatelessWidget {
  const SquareTileGrid({
    super.key,
    required this.itemCount,
    required this.columns,
    required this.itemBuilder,
    this.spacing = 6,
  });

  final int itemCount;
  final int columns;
  final IndexedWidgetBuilder itemBuilder;
  final double spacing;

  @override
  Widget build(BuildContext context) {
    final rows = (itemCount / columns).ceil();

    return LayoutBuilder(
      builder: (context, constraints) {
        // Flutter's logical pixel is calibrated to the same ~160px/inch
        // density Android's dp uses, so this converts a physical cm into
        // logical pixels without needing a platform channel.
        const pxPerCm = 160 / 2.54;
        const minTileSize = pxPerCm;

        final widthBasedSize = (constraints.maxWidth - spacing * (columns - 1)) / columns;
        final heightBasedSize = (constraints.maxHeight - spacing * (rows - 1)) / rows;
        final tileSize = max(minTileSize, min(widthBasedSize, heightBasedSize));

        final gridWidth = tileSize * columns + spacing * (columns - 1);
        final gridHeight = tileSize * rows + spacing * (rows - 1);

        final grid = GridView.builder(
          physics: const NeverScrollableScrollPhysics(),
          itemCount: itemCount,
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: columns,
            crossAxisSpacing: spacing,
            mainAxisSpacing: spacing,
            childAspectRatio: 1,
          ),
          itemBuilder: itemBuilder,
        );

        return Align(
          alignment: Alignment.topCenter,
          child: SizedBox(
            width: gridWidth,
            height: min(gridHeight, constraints.maxHeight),
            child: SingleChildScrollView(
              physics: gridHeight > constraints.maxHeight
                  ? const ClampingScrollPhysics()
                  : const NeverScrollableScrollPhysics(),
              child: SizedBox(height: gridHeight, child: grid),
            ),
          ),
        );
      },
    );
  }
}
