use solana_program::{
    account_info::{next_account_info, AccountInfo},
    entrypoint,
    entrypoint::ProgramResult,
    msg,
    pubkey::Pubkey,
    program_error::ProgramError,
};

/// Команды Write-программы
#[repr(u8)]
pub enum WriteCommand {
    Write = 0,
    // Можно добавить другие команды для расширения
}

entrypoint!(process_instruction);

pub fn process_instruction(
    _program_id: &Pubkey,
    accounts: &[AccountInfo],
    instruction_data: &[u8],
) -> ProgramResult {
    let account_info_iter = &mut accounts.iter();
    let target_account = next_account_info(account_info_iter)?;

    if instruction_data.len() < 5 {
        msg!("Instruction data too short");
        return Err(ProgramError::InvalidInstructionData);
    }

    let command = instruction_data[0];
    let offset = u32::from_le_bytes(instruction_data[1..5].try_into().unwrap()) as usize;
    let payload = &instruction_data[5..];

    match command {
        0 => { // Write
            let data_len = target_account.data_len();
            if offset + payload.len() > data_len {
                msg!("Write would overflow account data");
                return Err(ProgramError::InvalidAccountData);
            }
            let data = &mut target_account.data.borrow_mut();
            data[offset..offset + payload.len()].copy_from_slice(payload);
            msg!("Write complete at offset {}", offset);
            Ok(())
        }
        _ => {
            msg!("Unknown command");
            Err(ProgramError::InvalidInstructionData)
        }
    }
}
