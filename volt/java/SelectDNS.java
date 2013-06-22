import org.voltdb.*;

public class SelectDNS extends VoltProcedure {

  public final SQLStmt sql = new SQLStmt(
      "SELECT * FROM DNS " +
      " WHERE DOMAIN LIKE ?;"
  );

  public VoltTable[] run( String language)
      throws VoltAbortException {
          voltQueueSQL( sql, language );
          return voltExecuteSQL();
      }
}
