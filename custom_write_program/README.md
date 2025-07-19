# Custom Write Program for Solana

## Возможности
- Запись произвольных байтов в data любого writable аккаунта по offset.
- (Расширяемо для MemoryRegion, Cell, heap-манипуляций).

## Сборка
```bash
cargo build-bpf
```
или
```bash
anchor build
```

## Деплой
```bash
solana program deploy ./target/deploy/custom_write_program.so
```

## Использование
- Вставьте program_id в Python-эксплойт.
- Используйте метод _create_memory_write_transaction для записи данных.
