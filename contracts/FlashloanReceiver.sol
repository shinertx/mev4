// SPDX-License-Identifier: MIT
pragma solidity ^0.8.10;

import {IPool} from "@aave/core-v3/contracts/interfaces/IPool.sol";
import {IERC20} from "@aave/core-v3/contracts/dependencies/openzeppelin/contracts/IERC20.sol";

/**
 * @title FlashloanReceiver
 * @author MEV-OG
 * @notice This contract receives a flash loan from Aave V3, executes
 * arbitrary logic provided via calldata, and repays the loan.
 * IT IS HIGHLY UNSECURE BY DESIGN to be flexible. In a real-world scenario,
 * it would need strict access controls and checks on what calldata can be executed.
 */
contract FlashloanReceiver {
    address private owner;
    IPool private immutable POOL;

    constructor(address _poolAddress) {
        owner = msg.sender;
        POOL = IPool(_poolAddress);
    }

    /**
     * @dev This is the function called by the Aave Pool contract after lending the funds.
     */
    function executeOperation(
        address[] calldata assets,
        uint256[] calldata amounts,
        uint256[] calldata premiums,
        address initiator,
        bytes calldata params
    ) external returns (bool) {
        require(msg.sender == address(POOL), "Caller must be Aave V3 Pool");
        require(initiator == owner, "Only owner can initiate flash loans");

        // --- 1. Execute Arbitrary Operations ---
        // params will contain the sequence of calls to make (e.g., swap on Uniswap).
        // This is the core of the strategy execution.
        // The contract executes this by using address.call(calldata).
        (bool success, ) = address(this).call(params);
        require(success, "Execution of operations failed");

        // --- 2. Repay the Loan + Premium ---
        for (uint i = 0; i < assets.length; i++) {
            uint256 amountToRepay = amounts[i] + premiums[i];
            IERC20(assets[i]).approve(address(POOL), amountToRepay);
        }

        return true;
    }

    /**
     * @dev Main entry point for the owner to initiate a flash loan.
     */
    function initiateFlashloan(
        address[] calldata assets,
        uint256[] calldata amounts,
        bytes calldata params
    ) external {
        require(msg.sender == owner, "Only owner can call this");
        POOL.flashLoan(address(this), assets, amounts, new uint256[](assets.length), msg.sender, params, 0);
    }

    // A strategy might require this contract to call another contract (e.g., Uniswap).
    // This function allows the contract to execute external calls encoded in `params`.
    function executeCall(address target, bytes calldata data) external {
        require(msg.sender == address(this), "Internal call only");
        (bool success, ) = target.call(data);
        require(success, "External call failed");
    }

    receive() external payable {}
}
